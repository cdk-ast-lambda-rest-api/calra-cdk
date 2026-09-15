import pytest
from aws_cdk import App, Stack, aws_apigateway as apigateway
from aws_cdk import aws_cognito as cognito, aws_lambda as lambda_

from conftest import make_graph, make_method
from lambda_api_decorators_cdk import ResourceBuilder
from lambda_api_decorators_cdk.ast_helper import DecoratorInvocation
from lambda_api_decorators_cdk import resource_builder as module


class RestResource:
    path = "/"

    def __init__(self, defaults=None):
        self.defaults = defaults
        self.calls = []

    def add_method(self, method, integration, **options):
        self.calls.append((method, options))


def invocation(name, *args):
    return DecoratorInvocation(name, args, ())


@pytest.fixture(params=["cognito", "token"])
def rest_authorizer(request):
    stack = Stack(App(), "Stack")
    if request.param == "cognito":
        pool = cognito.UserPool(stack, "Pool")
        return apigateway.CognitoUserPoolsAuthorizer(
            stack, "Users", cognito_user_pools=[pool]
        )
    handler = lambda_.Function(
        stack,
        "AuthFunction",
        runtime=lambda_.Runtime.PYTHON_3_12,
        handler="index.handler",
        code=lambda_.Code.from_inline("def handler(event, context): return {}"),
    )
    return apigateway.TokenAuthorizer(stack, "Users", handler=handler)


@pytest.mark.parametrize(
    "decorators", [[], [invocation("authorizer", "users")]]
)
def test_rest_protected_route_passes_authorizer_and_its_type(
    monkeypatch, rest_authorizer, decorators
):
    builder = ResourceBuilder(
        authorizers={"users": rest_authorizer}, default_authorizer="users"
    )
    monkeypatch.setattr(builder, "build_lambda_function", lambda *args: object())
    monkeypatch.setattr(module.apigateway, "LambdaIntegration", lambda value: value)
    api = RestResource()
    builder.build_from_graph(
        object(), make_graph(methods=[make_method(decorators=decorators)]), api
    )
    options = api.calls[0][1]
    selected = options.authorizer if hasattr(options, "authorizer") else options["authorizer"]
    assert selected is rest_authorizer
    authorization_type = (
        options.authorization_type
        if hasattr(options, "authorization_type")
        else options["authorization_type"]
    )
    assert authorization_type is rest_authorizer.authorization_type


@pytest.mark.parametrize("explicit_public", [False, True])
def test_rest_public_route_explicitly_overrides_api_method_defaults(
    monkeypatch, rest_authorizer, explicit_public
):
    builder = ResourceBuilder(
        authorizers={"users": rest_authorizer},
        default_authorizer="users" if explicit_public else None,
    )
    decorators = [invocation("public")] if explicit_public else []
    monkeypatch.setattr(builder, "build_lambda_function", lambda *args: object())
    monkeypatch.setattr(module.apigateway, "LambdaIntegration", lambda value: value)
    api = RestResource(defaults={"authorizer": rest_authorizer})
    builder.build_from_graph(
        object(), make_graph(methods=[make_method(decorators=decorators)]), api
    )
    options = api.calls[0][1]
    assert options is not None
    selected = options.authorizer if hasattr(options, "authorizer") else options.get("authorizer")
    authorization_type = (
        options.authorization_type
        if hasattr(options, "authorization_type")
        else options["authorization_type"]
    )
    assert selected is None
    assert authorization_type is apigateway.AuthorizationType.NONE
