import pytest
from aws_cdk import App, Stack, Duration, aws_lambda as lambda_
from aws_cdk import aws_apigatewayv2_authorizers as authorizers

from conftest import make_graph, make_method
from lambda_api_decorators_cdk import ResourceBuilder
from lambda_api_decorators_cdk.ast_helper import DecoratorInvocation
from lambda_api_decorators_cdk import resource_builder as module


class HttpApi:
    def __init__(self):
        self.routes = []

    def add_routes(self, **kwargs):
        self.routes.append(kwargs)


@pytest.mark.parametrize(
    "resolved",
    [
        authorizers.HttpJwtAuthorizer(
            "Jwt", "https://issuer.example", jwt_audience=["audience"]
        ),
        authorizers.HttpIamAuthorizer(),
    ],
)
@pytest.mark.parametrize("explicit", [False, True])
def test_http_protected_route_passes_resolved_authorizer(
    monkeypatch, resolved, explicit
):
    builder = ResourceBuilder(authorizers={"users": resolved}, default_authorizer="users")
    decorators = (
        [DecoratorInvocation("authorizer", ("users",), ())] if explicit else []
    )
    monkeypatch.setattr(builder, "build_lambda_function", lambda *args: object())
    monkeypatch.setattr(module.integrations, "HttpLambdaIntegration", lambda *args: object())
    api = HttpApi()
    builder.build_http_from_graph(
        object(), make_graph(methods=[make_method(decorators=decorators)]), api
    )
    assert api.routes[0]["authorizer"] is resolved


@pytest.mark.parametrize("default,decorators", [(None, []), ("users", [DecoratorInvocation("public", (), ())])])
def test_http_public_route_explicitly_uses_none_authorizer(
    monkeypatch, default, decorators
):
    protected = authorizers.HttpIamAuthorizer()
    builder = ResourceBuilder(authorizers={"users": protected}, default_authorizer=default)
    monkeypatch.setattr(builder, "build_lambda_function", lambda *args: object())
    monkeypatch.setattr(module.integrations, "HttpLambdaIntegration", lambda *args: object())
    api = HttpApi()
    builder.build_http_from_graph(
        object(), make_graph(methods=[make_method(decorators=decorators)]), api
    )
    assert isinstance(api.routes[0]["authorizer"], authorizers.HttpNoneAuthorizer)


def test_http_lambda_authorizer_is_supported(monkeypatch):
    stack = Stack(App(), "Stack")
    handler = lambda_.Function(
        stack,
        "AuthFunction",
        runtime=lambda_.Runtime.PYTHON_3_12,
        handler="index.handler",
        code=lambda_.Code.from_inline("def handler(event, context): return {}"),
    )
    resolved = authorizers.HttpLambdaAuthorizer(
        "Users",
        handler,
        response_types=[authorizers.HttpLambdaResponseType.SIMPLE],
        results_cache_ttl=Duration.seconds(0),
    )
    builder = ResourceBuilder(authorizers={"users": resolved}, default_authorizer="users")
    monkeypatch.setattr(builder, "build_lambda_function", lambda *args: object())
    monkeypatch.setattr(module.integrations, "HttpLambdaIntegration", lambda *args: object())
    api = HttpApi()
    builder.build_http_from_graph(
        stack, make_graph(methods=[make_method()]), api
    )
    assert api.routes[0]["authorizer"] is resolved
