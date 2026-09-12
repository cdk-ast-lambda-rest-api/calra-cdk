from enum import Enum
from pathlib import Path

import pytest

from lambda_api_decorators_cdk import ResourceBuilder
from lambda_api_decorators_cdk import resource_builder as module


class _FutureSourceLayout(Enum):
    ROOT = "root"
    SERVICE = "service"


def source_layout(name):
    try:
        from lambda_api_decorators_cdk import SourceLayout
    except ImportError:
        SourceLayout = _FutureSourceLayout
    return SourceLayout[name]


class FakeRestResource:
    def __init__(self, path="/"):
        self.path = path

    def add_resource(self, name):
        return FakeRestResource(self.path.rstrip("/") + "/" + name)

    def add_method(self, method, integration):
        pass


class FakeHttpApi:
    def add_routes(self, **kwargs):
        pass


@pytest.fixture
def capture_python_functions(monkeypatch):
    calls = []

    def fake(construct, construct_id, **kwargs):
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(module._lambda_python, "PythonFunction", fake)
    monkeypatch.setattr(module.apigateway, "LambdaIntegration", lambda value: value)
    monkeypatch.setattr(
        module.integrations, "HttpLambdaIntegration", lambda name, value: value)
    return calls


def write_handler(path, handler="handle", route=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    route = route or f"/{path.stem}"
    path.write_text(
        f'@GET("{route}")\ndef {handler}(event, context):\n    pass\n',
        encoding="utf-8",
    )


def build_source(builder, api_kind, lambda_path, layout=None):
    if api_kind == "rest":
        args = (object(), FakeRestResource(), str(lambda_path))
        if layout is None:
            builder.build(*args)
        else:
            builder.build(*args, source_layout=layout)
    else:
        args = (object(), FakeHttpApi(), str(lambda_path))
        if layout is None:
            builder.build_http(*args)
        else:
            builder.build_http(*args, source_layout=layout)


def triples(calls):
    return [(Path(call["entry"]), call["index"], call["handler"]) for call in calls]


@pytest.mark.parametrize("explicit", [False, True])
def test_root_layout_uses_lambda_path_for_root_nested_and_deep_handlers(
        tmp_path, builder, capture_python_functions, explicit):
    root = tmp_path / "lambdas"
    write_handler(root / "health.py", "health_check", "/health")
    write_handler(root / "users" / "create.py", "create_user", "/users")
    write_handler(
        root / "orders" / "handlers" / "admin" / "create.py",
        "create_order", "/orders")

    layout = source_layout("ROOT") if explicit else None
    build_source(builder, "rest", root, layout)

    assert set(triples(capture_python_functions)) == {
        (root, "health.py", "health_check"),
        (root, "users/create.py", "create_user"),
        (root, "orders/handlers/admin/create.py", "create_order"),
    }


def test_root_layout_supports_relative_lambda_path(
        tmp_path, monkeypatch, builder, capture_python_functions):
    root = tmp_path / "project" / "lambdas"
    write_handler(root / "users" / "create.py", "create_user")
    monkeypatch.chdir(tmp_path / "project")

    build_source(builder, "rest", Path("lambdas"))

    entry, index, handler = triples(capture_python_functions)[0]
    assert entry.resolve() == root.resolve()
    assert (index, handler) == ("users/create.py", "create_user")


def test_service_layout_uses_first_directory_as_source_boundary(
        tmp_path, builder, capture_python_functions):
    root = tmp_path / "services"
    write_handler(root / "orders" / "handlers" / "create.py", "create_order")
    write_handler(
        root / "orders" / "handlers" / "admin" / "create.py",
        "admin_create_order", "/admin-orders")
    write_handler(root / "orders" / "domain" / "reconcile.py", "reconcile")
    write_handler(root / "orders" / "repositories" / "audit.py", "audit")
    write_handler(root / "users" / "handlers" / "create.py", "create_user")

    build_source(builder, "rest", root, source_layout("SERVICE"))

    assert set(triples(capture_python_functions)) == {
        (root / "orders", "handlers/create.py", "create_order"),
        (root / "orders", "handlers/admin/create.py", "admin_create_order"),
        (root / "orders", "domain/reconcile.py", "reconcile"),
        (root / "orders", "repositories/audit.py", "audit"),
        (root / "users", "handlers/create.py", "create_user"),
    }


def test_service_layout_rejects_root_handler_before_python_function(
        tmp_path, builder, capture_python_functions):
    root = tmp_path / "services"
    write_handler(root / "health.py", "health_check")

    with pytest.raises(ValueError, match=r"(?i)service.*first.level.*director"):
        build_source(builder, "rest", root, source_layout("SERVICE"))
    assert capture_python_functions == []


@pytest.mark.parametrize("layout_name, relative_file, expected_entry, expected_index", [
    ("ROOT", "orders/handlers/create.py", "", "orders/handlers/create.py"),
    ("SERVICE", "orders/handlers/create.py", "orders", "handlers/create.py"),
])
@pytest.mark.parametrize("api_kind", ["rest", "http"])
def test_rest_and_http_have_identical_source_layout_semantics(
        tmp_path, builder, capture_python_functions, layout_name, relative_file,
        expected_entry, expected_index, api_kind):
    root = tmp_path / ("lambdas" if layout_name == "ROOT" else "services")
    write_handler(root / relative_file, "dispatch")

    build_source(builder, api_kind, root, source_layout(layout_name))

    assert triples(capture_python_functions) == [
        (root / expected_entry, expected_index, "dispatch")]


@pytest.mark.parametrize("api_kind", ["rest", "http"])
@pytest.mark.parametrize("value", ["root", "service"])
def test_resource_builder_rejects_string_source_layout(
        tmp_path, builder, capture_python_functions, api_kind, value):
    root = tmp_path / "lambdas"
    write_handler(root / "handler.py")

    with pytest.raises(TypeError):
        build_source(builder, api_kind, root, value)
    assert capture_python_functions == []
