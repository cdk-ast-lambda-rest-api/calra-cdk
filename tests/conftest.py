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
    return Method(directory, file, handler, method, decorators or {})


def make_graph(path="/", methods=()):
    resource = Resource(path)
    for method in methods:
        resource.add_method(method)
    return resource
