import inspect
from dataclasses import dataclass
from pathlib import Path

import pytest
from aws_cdk import App, Stack
from aws_cdk import aws_lambda as lambda_

from lambda_api_decorators_cdk import (
    ApiType,
    LambdaApi,
    LambdaApiConfig,
    ResourceBuilder,
    SourceLayout,
)
from lambda_api_decorators_cdk import resource_builder as module
from test_http_builder import FakeHttpApi
from test_rest_builder import FakeRestResource


@dataclass
class ExplicitLayer:
    compatible_runtimes: object
    layer_version_arn: str = "arn:test:layer"


class UnreadableLayer:
    layer_version_arn = "arn:test:unreadable"

    @property
    def compatible_runtimes(self):
        raise RuntimeError("compatibility unavailable")


def _write_handler(path, *, route="/", runtime=None, layers=()):
    decorators = [f'@GET("{route}")']
    if runtime is not None:
        decorators.append(f'@runtime("{runtime}")')
    for layer in layers:
        decorators.append(f'@layer("{layer}")')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(decorators) + "\ndef handle(event, context): pass\n")


@pytest.fixture
def recording_boundaries(monkeypatch):
    layers = []
    functions = []

    def python_layer(scope, construct_id, **kwargs):
        value = ExplicitLayer(kwargs["compatible_runtimes"], f"arn:test:{construct_id}")
        layers.append({
            "scope": scope,
            "construct_id": construct_id,
            "kwargs": kwargs,
            "value": value,
        })
        return value

    def python_function(scope, construct_id, **kwargs):
        value = object()
        functions.append({
            "scope": scope,
            "construct_id": construct_id,
            "kwargs": kwargs,
            "value": value,
        })
        return value

    monkeypatch.setattr(module._lambda_python, "PythonLayerVersion", python_layer)
    monkeypatch.setattr(module._lambda_python, "PythonFunction", python_function)
    monkeypatch.setattr(module.apigateway, "LambdaIntegration", lambda value: value)
    monkeypatch.setattr(
        module.integrations, "HttpLambdaIntegration", lambda _id, value: value)
    return layers, functions


def _builder(runtime=lambda_.Runtime.PYTHON_3_12):
    return ResourceBuilder(
        default_runtime=runtime,
        common_layers=[],
        common_security_groups=[],
        common_environments={},
        custom_runtimes={},
        custom_roles={},
        custom_layers={},
        custom_environments={},
        custom_security_groups={},
        custom_vpcs={},
    )


def _build(builder, kind, owner, lambda_path, layers_path, source_layout=SourceLayout.ROOT):
    # Keep downstream contracts executable while production lacks the future
    # keyword. The dedicated signature test still requires that public change.
    if kind == "rest":
        method, api = builder.build, FakeRestResource()
    else:
        method, api = builder.build_http, FakeHttpApi()
    kwargs = {"source_layout": source_layout}
    if "layers_path" in inspect.signature(method).parameters:
        kwargs["layers_path"] = str(layers_path)
    return method(owner, api, str(lambda_path), **kwargs)


def test_resource_builder_boundaries_define_optional_layers_path():
    for method in (ResourceBuilder.build, ResourceBuilder.build_http):
        parameters = inspect.signature(method).parameters
        assert list(parameters)[-1] == "layers_path"
        assert parameters["layers_path"].default is None
    assert "layers_path" not in inspect.signature(ResourceBuilder.__init__).parameters
    assert "layers_path" not in inspect.signature(ResourceBuilder.build_from_graph).parameters
    assert "layers_path" not in inspect.signature(ResourceBuilder.build_http_from_graph).parameters


def test_lambda_api_config_does_not_accept_or_store_layers_path():
    assert "layers_path" not in inspect.signature(LambdaApiConfig.__init__).parameters
    config = LambdaApiConfig()
    assert not hasattr(config, "layers_path")


@pytest.mark.parametrize("kind", ["rest", "http"])
def test_omitted_layers_path_preserves_existing_direct_builder_behavior(
        tmp_path, recording_boundaries, kind):
    lambda_path = tmp_path / "lambdas"
    _write_handler(lambda_path / "handler.py")
    builder = _builder()
    if kind == "rest":
        builder.build(object(), FakeRestResource(), str(lambda_path))
    else:
        builder.build_http(object(), FakeHttpApi(), str(lambda_path))
    layers, functions = recording_boundaries
    assert layers == []
    assert len(functions) == 1


@pytest.mark.parametrize("kind", ["rest", "http"])
@pytest.mark.parametrize("invalid_kind", ["missing", "file"])
def test_invalid_explicit_layers_path_fails_before_construction(
        tmp_path, recording_boundaries, kind, invalid_kind):
    lambda_path = tmp_path / "lambdas"
    _write_handler(lambda_path / "handler.py", layers=("common",))
    layers_path = tmp_path / "layers"
    if invalid_kind == "file":
        layers_path.write_text("not a directory")
    with pytest.raises(ValueError):
        _build(_builder(), kind, object(), lambda_path, layers_path)
    assert recording_boundaries == ([], [])


@pytest.mark.parametrize("kind", ["rest", "http"])
def test_empty_layers_directory_is_valid_and_creates_nothing(
        tmp_path, recording_boundaries, kind):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(lambda_path / "handler.py")
    layers_path.mkdir()
    _build(_builder(), kind, object(), lambda_path, layers_path)
    layers, functions = recording_boundaries
    assert layers == []
    assert len(functions) == 1


def test_unused_discovered_directory_is_not_constructed(tmp_path, recording_boundaries):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(lambda_path / "handler.py")
    (layers_path / "unused").mkdir(parents=True)
    _build(_builder(), "rest", object(), lambda_path, layers_path)
    assert recording_boundaries[0] == []


def test_direct_folder_is_one_layer_and_nested_folders_are_its_source(
        tmp_path, recording_boundaries):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(lambda_path / "handler.py", layers=("common",))
    (layers_path / "common" / "nested").mkdir(parents=True)
    _build(_builder(), "rest", object(), lambda_path, layers_path)
    created = recording_boundaries[0]
    assert len(created) == 1
    assert Path(created[0]["kwargs"]["entry"]).resolve() == (layers_path / "common").resolve()
    assert created[0]["construct_id"] == "AutodiscoveredLayer:common"


@pytest.mark.parametrize("name,kind", [
    ("ordinary.txt", "file"),
    (".hidden", "directory"),
    (".venv", "directory"),
    ("__pycache__", "directory"),
    ("file-link", "file-link"),
    ("broken-link", "broken-link"),
])
def test_ineligible_direct_entries_do_not_resolve_as_layers(
        tmp_path, recording_boundaries, name, kind):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(lambda_path / "handler.py", layers=(name,))
    layers_path.mkdir()
    entry = layers_path / name
    if kind == "directory":
        entry.mkdir()
    elif kind == "file":
        entry.write_text("ignored")
    elif kind == "file-link":
        target = tmp_path / "target.txt"
        target.write_text("ignored")
        entry.symlink_to(target)
    else:
        entry.symlink_to(tmp_path / "missing")
    with pytest.raises(KeyError):
        _build(_builder(), "rest", object(), lambda_path, layers_path)
    assert recording_boundaries == ([], [])


def test_directory_symlink_is_an_eligible_direct_layer(tmp_path, recording_boundaries):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(lambda_path / "handler.py", layers=("linked",))
    target = tmp_path / "target"
    target.mkdir()
    layers_path.mkdir()
    (layers_path / "linked").symlink_to(target, target_is_directory=True)
    _build(_builder(), "rest", object(), lambda_path, layers_path)
    assert recording_boundaries[0][0]["construct_id"] == "AutodiscoveredLayer:linked"


def test_exact_names_and_deterministic_directory_order(tmp_path, recording_boundaries):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    names = ["foo_bar", "dto-message-services", "with space", "FooBar", "foo-bar"]
    _write_handler(lambda_path / "handler.py", layers=names)
    for name in reversed(names):
        (layers_path / name).mkdir(parents=True)
    _build(_builder(), "rest", object(), lambda_path, layers_path)
    assert [item["construct_id"] for item in recording_boundaries[0]] == [
        f"AutodiscoveredLayer:{name}" for name in sorted(names)
    ]


def test_explicit_override_wins_without_constructing_discovered_folder(
        tmp_path, recording_boundaries, caplog):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(lambda_path / "handler.py", layers=("database",))
    (layers_path / "database").mkdir(parents=True)
    explicit = ExplicitLayer([lambda_.Runtime.PYTHON_3_12])
    builder = _builder()
    builder.add_custom_layer("database", explicit)
    _build(builder, "rest", object(), lambda_path, layers_path)
    layers, functions = recording_boundaries
    assert layers == []
    assert functions[0]["kwargs"]["layers"] == [explicit]
    assert caplog.records == []


def test_unknown_and_nested_only_layer_names_remain_strict(
        tmp_path, recording_boundaries):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(lambda_path / "handler.py", layers=("nested",))
    (layers_path / "parent" / "nested").mkdir(parents=True)
    with pytest.raises(KeyError):
        _build(_builder(), "rest", object(), lambda_path, layers_path)
    assert recording_boundaries == ([], [])


def test_runtime_accumulation_uses_canonical_method_order_and_name_deduplication(
        tmp_path, recording_boundaries):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    # Creation order intentionally differs from canonical source-path order.
    _write_handler(lambda_path / "z.py", route="/z", runtime="py13", layers=("common",))
    _write_handler(lambda_path / "a.py", route="/a", runtime="python3.12", layers=("common",))
    _write_handler(lambda_path / "b.py", route="/b", runtime="py12-proxy", layers=("common",))
    (layers_path / "common").mkdir(parents=True)
    builder = _builder(lambda_.Runtime.PYTHON_3_11)
    builder.add_custom_runtime("py13", lambda_.Runtime.PYTHON_3_13)
    first_python_3_12 = lambda_.Runtime.PYTHON_3_12
    equivalent_python_3_12 = lambda_.Runtime.PYTHON_3_12
    assert equivalent_python_3_12 is not first_python_3_12
    assert equivalent_python_3_12.name == first_python_3_12.name == "python3.12"
    assert equivalent_python_3_12.family is lambda_.RuntimeFamily.PYTHON
    builder.add_custom_runtime("py12-proxy", equivalent_python_3_12)
    _build(builder, "rest", object(), lambda_path, layers_path)
    layers, functions = recording_boundaries
    assert len(layers) == 1
    assert [runtime.name for runtime in layers[0]["kwargs"]["compatible_runtimes"]] == [
        "python3.12", "python3.13"
    ]
    assert sorted(item["kwargs"]["runtime"].name for item in functions) == [
        "python3.12", "python3.12", "python3.13"
    ]


@pytest.mark.parametrize("runtime_key,expected", [
    (None, "python3.11"),
    ("python3.12", "python3.12"),
    ("custom", "python3.13"),
])
def test_layer_analysis_and_python_function_share_effective_runtime(
        tmp_path, recording_boundaries, runtime_key, expected):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(lambda_path / "handler.py", runtime=runtime_key, layers=("common",))
    (layers_path / "common").mkdir(parents=True)
    builder = _builder(lambda_.Runtime.PYTHON_3_11)
    builder.add_custom_runtime("custom", lambda_.Runtime.PYTHON_3_13)
    _build(builder, "rest", object(), lambda_path, layers_path)
    layers, functions = recording_boundaries
    assert layers[0]["kwargs"]["compatible_runtimes"][0].name == expected
    assert functions[0]["kwargs"]["runtime"].name == expected


@pytest.mark.parametrize("runtime", [None, lambda_.Runtime.NODEJS_20_X])
def test_autodiscovered_layer_requires_an_effective_python_runtime(
        tmp_path, recording_boundaries, runtime):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(lambda_path / "handler.py", layers=("common",))
    (layers_path / "common").mkdir(parents=True)
    with pytest.raises((TypeError, ValueError)):
        _build(_builder(runtime), "rest", object(), lambda_path, layers_path)
    assert recording_boundaries == ([], [])


@pytest.mark.parametrize("compatibility,accepted", [
    ([lambda_.Runtime.PYTHON_3_12], True),
    ([lambda_.Runtime.PYTHON_3_11], False),
    (None, True),
    (lambda_.Runtime.ALL, True),
])
def test_explicit_named_layer_enforces_cdk_compatibility_contract(
        tmp_path, recording_boundaries, compatibility, accepted):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(lambda_path / "handler.py", layers=("database",))
    layers_path.mkdir()
    layer = ExplicitLayer(compatibility)
    builder = _builder()
    builder.add_custom_layer("database", layer)
    if accepted:
        _build(builder, "rest", object(), lambda_path, layers_path)
        assert recording_boundaries[1][0]["kwargs"]["layers"] == [layer]
    else:
        with pytest.raises(ValueError, match="database.*python3.12|python3.12.*database"):
            _build(builder, "rest", object(), lambda_path, layers_path)
        assert recording_boundaries[1] == []


def test_unreadable_explicit_layer_compatibility_fails_before_lambda(
        tmp_path, recording_boundaries):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(lambda_path / "handler.py", layers=("database",))
    layers_path.mkdir()
    builder = _builder()
    builder.add_custom_layer("database", UnreadableLayer())
    with pytest.raises((TypeError, ValueError), match="database|compatib"):
        _build(builder, "rest", object(), lambda_path, layers_path)
    assert recording_boundaries[1] == []


@pytest.mark.parametrize("compatible", [True, False])
def test_common_layer_compatibility_is_checked_before_any_lambda(
        tmp_path, recording_boundaries, compatible):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(lambda_path / "handler.py")
    layers_path.mkdir()
    runtime = lambda_.Runtime.PYTHON_3_12 if compatible else lambda_.Runtime.PYTHON_3_11
    layer = ExplicitLayer([runtime], "arn:test:common")
    builder = _builder()
    builder.add_common_layer(layer)
    if compatible:
        _build(builder, "rest", object(), lambda_path, layers_path)
        assert recording_boundaries[1][0]["kwargs"]["layers"] == [layer]
    else:
        with pytest.raises(ValueError, match="python3.12"):
            _build(builder, "rest", object(), lambda_path, layers_path)
        assert recording_boundaries[1] == []


@pytest.mark.parametrize("kind", ["attributes-compatible", "attributes-incompatible", "arn"])
def test_imported_layer_uses_exposed_cdk_contract_not_remote_artifact_truth(
        tmp_path, recording_boundaries, kind):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(lambda_path / "handler.py", layers=("imported",))
    layers_path.mkdir()
    stack = Stack(App(), f"Stack-{kind}")
    arn = "arn:aws:lambda:us-east-1:123456789012:layer:external:1"
    if kind == "arn":
        layer = lambda_.LayerVersion.from_layer_version_arn(stack, "Layer", arn)
    else:
        declared = (lambda_.Runtime.PYTHON_3_12 if kind == "attributes-compatible"
                    else lambda_.Runtime.PYTHON_3_11)
        layer = lambda_.LayerVersion.from_layer_version_attributes(
            stack, "Layer", layer_version_arn=arn, compatible_runtimes=[declared])
    builder = _builder()
    builder.add_custom_layer("imported", layer)
    if kind == "attributes-incompatible":
        with pytest.raises(ValueError):
            _build(builder, "rest", object(), lambda_path, layers_path)
        assert recording_boundaries[1] == []
    else:
        _build(builder, "rest", object(), lambda_path, layers_path)
        assert recording_boundaries[1][0]["kwargs"]["layers"] == [layer]


def test_mixed_explicit_and_discovered_layers_preserve_lambda_order(
        tmp_path, recording_boundaries):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(
        lambda_path / "handler.py", layers=("explicit-db", "common"))
    (layers_path / "common").mkdir(parents=True)
    explicit = ExplicitLayer([lambda_.Runtime.PYTHON_3_12])
    builder = _builder()
    global_layer = ExplicitLayer(None, "arn:test:global")
    builder.add_common_layer(global_layer)
    builder.add_custom_layer("explicit-db", explicit)
    _build(builder, "rest", object(), lambda_path, layers_path)
    discovered = recording_boundaries[0][0]["value"]
    assert recording_boundaries[1][0]["kwargs"]["layers"] == [
        global_layer, explicit, discovered
    ]


@pytest.mark.parametrize("kind", ["rest", "http"])
@pytest.mark.parametrize("layout", [SourceLayout.ROOT, SourceLayout.SERVICE])
def test_rest_http_and_source_layout_have_identical_layer_semantics(
        tmp_path, recording_boundaries, kind, layout):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    handler = lambda_path / ("service/handler.py" if layout is SourceLayout.SERVICE
                             else "handler.py")
    _write_handler(handler, layers=("common",))
    (layers_path / "common").mkdir(parents=True)
    _build(_builder(), kind, object(), lambda_path, layers_path, layout)
    layer = recording_boundaries[0][0]
    assert Path(layer["kwargs"]["entry"]).resolve() == (layers_path / "common").resolve()
    assert [runtime.name for runtime in layer["kwargs"]["compatible_runtimes"]] == [
        "python3.12"
    ]


def test_autodiscovered_construct_uses_owner_exact_id_and_no_physical_name(
        tmp_path, recording_boundaries):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(lambda_path / "handler.py", layers=("foo-bar",))
    (layers_path / "foo-bar").mkdir(parents=True)
    owner = object()
    _build(_builder(), "rest", owner, lambda_path, layers_path)
    layer = recording_boundaries[0][0]
    assert layer["scope"] is owner
    assert layer["construct_id"] == "AutodiscoveredLayer:foo-bar"
    assert "layer_version_name" not in layer["kwargs"]


def test_reused_config_keeps_discovered_layers_isolated_per_lambda_api(
        tmp_path, recording_boundaries, monkeypatch):
    lambda_path, layers_path = tmp_path / "lambdas", tmp_path / "layers"
    _write_handler(lambda_path / "handler.py", layers=("common", "explicit"))
    (layers_path / "common").mkdir(parents=True)
    explicit = ExplicitLayer([lambda_.Runtime.PYTHON_3_12])
    config = LambdaApiConfig(runtime=lambda_.Runtime.PYTHON_3_12)
    config.add_custom_layer("explicit", explicit)
    snapshots = []
    original = LambdaApiConfig._create_resource_builder

    def capture_snapshot(self):
        result = original(self)
        monkeypatch.setattr(
            result, "build_from_graph", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            result, "build_http_from_graph", lambda *args, **kwargs: None)
        snapshots.append(result)
        return result

    monkeypatch.setattr(LambdaApiConfig, "_create_resource_builder", capture_snapshot)
    stack = Stack(App(), "Stack")
    first = LambdaApi(
        stack, "First", lambda_path=str(lambda_path), layers_path=str(layers_path),
        config=config)
    second = LambdaApi(
        stack, "Second", lambda_path=str(lambda_path), layers_path=str(layers_path),
        api_type=ApiType.HTTP, config=config,
    )
    layers, _functions = recording_boundaries
    assert snapshots[0] is not snapshots[1]
    assert snapshots[0].custom_layers is not snapshots[1].custom_layers
    assert snapshots[0].custom_layers["explicit"] is explicit
    assert snapshots[1].custom_layers["explicit"] is explicit
    assert snapshots[0].custom_layers["common"] is layers[0]["value"]
    assert snapshots[1].custom_layers["common"] is layers[1]["value"]
    assert not hasattr(config, "custom_layers")
    assert not hasattr(config, "layers_path")
    assert len(layers) == 2
    assert layers[0]["value"] is not layers[1]["value"]
    assert layers[0]["scope"] is first
    assert layers[1]["scope"] is second
