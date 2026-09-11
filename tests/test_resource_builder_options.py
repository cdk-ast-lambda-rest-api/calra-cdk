import pytest
from aws_cdk import Duration


def test_get_options_defaults_are_complete():
    from lambda_api_decorators_cdk import ResourceBuilder
    runtime, timeout, role, vpc = object(), Duration.seconds(8), object(), object()
    builder = ResourceBuilder(runtime, timeout, 256, vpc, role,
                              ["common-layer"], ["common-sg"], {"A": "common"},
                              {}, {}, {}, {}, {}, {})
    assert builder.get_options({}) == {
        "runtime": runtime, "timeout": timeout, "memory_size": 256,
        "role": role, "vpc": vpc, "layer": ["common-layer"],
        "security_group": ["common-sg"], "environment": {"A": "common"},
        "description": None, "name": None,
    }


def test_scalar_and_runtime_overrides(builder):
    runtime = object()
    builder.add_custom_runtime("custom", runtime)
    options = builder.get_options({"runtime": "custom", "timeout": 17,
                                   "memory_size": 1024, "name": "named",
                                   "description": "described"})
    assert options["runtime"] is runtime
    assert options["timeout"].to_seconds() == 17
    assert options["memory_size"] == 1024
    assert options["name"] == "named"
    assert options["description"] == "described"


@pytest.mark.parametrize("selection", ["one", ["one", "two"]])
def test_layers_append_after_common_layers(builder, selection):
    builder.common_layers.append("common")
    builder.add_custom_layer("one", "layer-1")
    builder.add_custom_layer("two", "layer-2")
    expected = ["common", "layer-1"] + (["layer-2"] if isinstance(selection, list) else [])
    assert builder.get_options({"layer": selection})["layer"] == expected


def test_environments_merge_and_custom_overrides_common(builder):
    builder.common_environments.update({"SHARED": "common", "COMMON": "yes"})
    builder.add_custom_environment("SHARED", "custom")
    builder.add_custom_environment("ONLY", "value")
    assert builder.get_options({"environment": ["SHARED", "ONLY"]})["environment"] == {
        "SHARED": "custom", "COMMON": "yes", "ONLY": "value"}


def test_custom_vpc_overrides_default(builder):
    builder.default_vpc = ("default", ["default-subnet"])
    builder.add_custom_vpc("selected", "custom", ["custom-subnet"])
    assert builder.get_options({"vpc": "selected"})["vpc"] == (
        "custom", ["custom-subnet"])


def test_role_decorator_resolves_to_scalar(builder):
    """EXPECTED BEHAVIOR / BUG REGRESSION: role currently calls append on scalar."""
    role = object()
    builder.add_custom_role("role", role)
    assert builder.get_options({"role": "role"})["role"] is role


def test_multiple_security_groups_use_security_group_registry(builder):
    """EXPECTED BEHAVIOR / BUG REGRESSION: list branch reads environments."""
    one, two = object(), object()
    builder.custom_security_groups.update({"one": one, "two": two})
    assert builder.get_options({"security_group": ["one", "two"]})["security_group"] == [one, two]


def test_single_security_group_appends_after_common(builder):
    custom = object()
    builder.common_security_groups.append("common")
    builder.custom_security_groups["custom"] = custom
    assert builder.get_options({"security_group": "custom"})["security_group"] == ["common", custom]


def test_repeated_get_options_does_not_mutate_common_containers(builder):
    builder.common_layers.append("common-layer")
    builder.common_security_groups.append("common-sg")
    builder.common_environments["COMMON"] = "value"
    builder.add_custom_layer("layer", "custom-layer")
    builder.custom_security_groups["sg"] = "custom-sg"
    builder.add_custom_environment("ENV", "custom")
    decorators = {"layer": "layer", "security_group": "sg", "environment": "ENV"}
    assert builder.get_options(decorators) == builder.get_options(decorators)
    assert builder.common_layers == ["common-layer"]
    assert builder.common_security_groups == ["common-sg"]
    assert builder.common_environments == {"COMMON": "value"}
