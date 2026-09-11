import pytest
from aws_cdk import Duration

from conftest import make_method
from lambda_api_decorators_cdk import resource_builder as module


@pytest.fixture
def capture_python_function(monkeypatch):
    calls = []
    def fake(construct, construct_id, **kwargs):
        result = object()
        calls.append((construct, construct_id, kwargs, result))
        return result
    monkeypatch.setattr(module._lambda_python, "PythonFunction", fake)
    return calls


def test_minimal_python_function_boundary(builder, capture_python_function):
    construct = object()
    result = builder.build_lambda_function(construct, make_method())
    owner, construct_id, kwargs, returned = capture_python_function[0]
    assert result is returned
    assert owner is construct
    assert construct_id == "handlerdotpy-handle"
    assert kwargs == {
        "function_name": "handlerdotpy-handle", "description": None,
        "entry": "lambdas", "index": "handler.py", "handler": "handle",
        "runtime": None, "timeout": None, "layers": [], "memory_size": None,
        "security_groups": [], "vpc": None, "vpc_subnets": None,
        "allow_public_subnet": False, "environment": {}, "role": None,
    }


def test_custom_scalar_python_function_arguments(builder, capture_python_function):
    runtime = object()
    builder.add_custom_runtime("runtime", runtime)
    method = make_method(decorators={"runtime": "runtime", "timeout": 9,
                                    "memory_size": 768, "name": "public-name",
                                    "description": "docs"})
    builder.build_lambda_function(object(), method)
    kwargs = capture_python_function[0][2]
    assert kwargs["runtime"] is runtime
    assert kwargs["timeout"].to_seconds() == 9
    assert kwargs["memory_size"] == 768
    assert kwargs["function_name"] == "public-name"
    assert kwargs["description"] == "docs"


def test_common_and_custom_layers_and_environment_reach_boundary(builder, capture_python_function):
    builder.common_layers.append("common")
    builder.add_custom_layer("selected", "custom")
    builder.common_environments.update({"A": "common", "B": "common"})
    builder.add_custom_environment("B", "custom")
    builder.build_lambda_function(object(), make_method(decorators={
        "layer": "selected", "environment": "B"}))
    kwargs = capture_python_function[0][2]
    assert kwargs["layers"] == ["common", "custom"]
    assert kwargs["environment"] == {"A": "common", "B": "custom"}


def test_custom_role_reaches_python_function(builder, capture_python_function):
    """EXPECTED BEHAVIOR / BUG REGRESSION: role option resolution is broken."""
    role = object()
    builder.add_custom_role("role", role)
    builder.build_lambda_function(object(), make_method(decorators={"role": "role"}))
    assert capture_python_function[0][2]["role"] is role


@pytest.mark.parametrize("decorators, expected", [
    ({}, ("default-vpc", ["default-subnet"])),
    ({"vpc": "selected"}, ("custom-vpc", ["custom-subnet"])),
])
def test_resolved_vpc_and_subnets_reach_python_function(
        builder, capture_python_function, decorators, expected):
    """EXPECTED BEHAVIOR / BUG REGRESSION: boundary hard-codes both to None."""
    builder.default_vpc = ("default-vpc", ["default-subnet"])
    builder.add_custom_vpc("selected", "custom-vpc", ["custom-subnet"])
    builder.build_lambda_function(object(), make_method(decorators=decorators))
    kwargs = capture_python_function[0][2]
    assert (kwargs["vpc"], kwargs["vpc_subnets"]) == expected


def test_vpc_security_groups_and_public_subnet_boundary(builder, capture_python_function):
    group = object()
    builder.default_vpc = ("vpc", ["subnet"])
    builder.common_security_groups.append(group)
    builder.build_lambda_function(object(), make_method())
    kwargs = capture_python_function[0][2]
    assert kwargs["security_groups"] == [group]
    assert kwargs["allow_public_subnet"] is False
