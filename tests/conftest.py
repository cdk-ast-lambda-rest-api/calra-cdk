import pytest

from lambda_api_decorators_cdk import ResourceBuilder
from lambda_api_decorators_cdk.ast_helper import Method, Resource


@pytest.fixture
def builder():
    """A builder whose mutable inputs are deliberately isolated per test."""
    return ResourceBuilder(
        common_layers=[], common_security_groups=[], common_environments={},
        custom_runtimes={}, custom_roles={}, custom_layers={},
        custom_environments={}, custom_security_groups={}, custom_vpcs={},
    )


def make_method(method="GET", path="/", decorators=None, file="handler.py",
                directory="lambdas", handler="handle"):
    return Method(
        directory, file, handler, method,
        decorators if decorators is not None else {},
    )


def make_graph(path="/", methods=()):
    resource = Resource(path)
    for method in methods:
        resource.add_method(method)
    return resource


def decorator_invocations(method):
    """Return the conceptual invocation schema without fixing its concrete type."""
    invocations = method.get_decorator_invocations()

    def field(invocation, name):
        if isinstance(invocation, dict):
            return invocation[name]
        return getattr(invocation, name)

    return [
        (
            field(invocation, "name"),
            tuple(field(invocation, "args")),
            tuple(field(invocation, "kwargs").items())
            if isinstance(field(invocation, "kwargs"), dict)
            else tuple(field(invocation, "kwargs")),
        )
        for invocation in invocations
    ]
