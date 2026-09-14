import pytest
from aws_cdk import App, Stack, aws_apigateway as apigateway
from aws_cdk import aws_apigatewayv2_authorizers as http_authorizers
from aws_cdk import aws_cognito as cognito

from conftest import make_graph, make_method
from lambda_api_decorators_cdk import ResourceBuilder
from lambda_api_decorators_cdk.ast_helper import DecoratorInvocation
from lambda_api_decorators_cdk import resource_builder as module


class FakeRestResource:
    path = "/"

    def __init__(self):
        self.methods = []

    def add_method(self, method, integration, options=None):
        self.methods.append((method, options or {}))


class FakeHttpApi:
    def __init__(self):
        self.routes = []

    def add_routes(self, **kwargs):
        self.routes.append(kwargs)


def auth(name=None):
    return [] if name == "inherit" else [
        DecoratorInvocation("public", (), ()) if name == "public"
        else DecoratorInvocation("authorizer", (name,), ())
    ]


@pytest.mark.parametrize(
    "default,route,expected",
    [
        ("users", "inherit", "users"),
        ("users", "admins", "admins"),
        ("users", "public", None),
        (None, "inherit", None),
        (None, "users", "users"),
        (None, "public", None),
    ],
)
def test_effective_authorization_has_three_distinct_states(
    monkeypatch, default, route, expected
):
    stack = Stack(App(), "ResolutionStack")
    pool = cognito.UserPool(stack, "Pool")
    users = apigateway.CognitoUserPoolsAuthorizer(stack, "Users", cognito_user_pools=[pool])
    admins = apigateway.CognitoUserPoolsAuthorizer(stack, "Admins", cognito_user_pools=[pool])
    builder = ResourceBuilder(
        authorizers={"users": users, "admins": admins},
        default_authorizer=default,
    )
    monkeypatch.setattr(builder, "build_lambda_function", lambda *args: object())
    monkeypatch.setattr(module.apigateway, "LambdaIntegration", lambda value: value)
    api = FakeRestResource()
    builder.build_from_graph(
        object(), make_graph(methods=[make_method(decorators=auth(route))]), api
    )
    assert api.methods[0][1].get("authorizer") is (
        None if expected is None else {"users": users, "admins": admins}[expected]
    )
    assert api.methods[0][1]["authorization_type"] is (
        apigateway.AuthorizationType.NONE
        if expected is None
        else api.methods[0][1]["authorizer"].authorization_type
    )


def test_missing_route_authorizer_key_is_a_hard_failure(monkeypatch):
    stack = Stack(App(), "MissingStack")
    pool = cognito.UserPool(stack, "Pool")
    users = apigateway.CognitoUserPoolsAuthorizer(stack, "Users", cognito_user_pools=[pool])
    builder = ResourceBuilder(authorizers={"users": users}, default_authorizer="users")
    monkeypatch.setattr(builder, "build_lambda_function", lambda *args: object())
    monkeypatch.setattr(module.apigateway, "LambdaIntegration", lambda value: value)
    method = make_method(decorators=auth("missing"))
    with pytest.raises((KeyError, ValueError), match="missing"):
        builder.build_from_graph(object(), make_graph(methods=[method]), FakeRestResource())


@pytest.mark.parametrize("family", ["REST", "HTTP"])
def test_wrong_authorizer_family_fails_at_build_with_key_and_family(monkeypatch, family):
    stack = Stack(App(), f"{family}Stack")
    pool = cognito.UserPool(stack, "Pool")
    rest = apigateway.CognitoUserPoolsAuthorizer(
        stack, "Rest", cognito_user_pools=[pool]
    )
    http = http_authorizers.HttpJwtAuthorizer(
        "Http", "https://issuer.example", jwt_audience=["audience"]
    )
    wrong = http if family == "REST" else rest
    builder = ResourceBuilder(authorizers={"wrong-key": wrong}, default_authorizer="wrong-key")
    monkeypatch.setattr(builder, "build_lambda_function", lambda *args: object())
    if family == "REST":
        monkeypatch.setattr(module.apigateway, "LambdaIntegration", lambda value: value)
        call = lambda: builder.build_from_graph(
            stack, make_graph(methods=[make_method()]), FakeRestResource()
        )
    else:
        monkeypatch.setattr(module.integrations, "HttpLambdaIntegration", lambda *args: object())
        call = lambda: builder.build_http_from_graph(
            stack, make_graph(methods=[make_method()]), FakeHttpApi()
        )
    with pytest.raises(TypeError, match=rf"(?is)wrong-key.*{family}|{family}.*wrong-key"):
        call()


def test_auth_metadata_never_enters_permission_application(monkeypatch):
    builder = ResourceBuilder(authorizers={"users": http_authorizers.HttpIamAuthorizer()}, default_authorizer="users")
    seen = []
    monkeypatch.setattr(builder, "_apply_dynamodb_grant", lambda *args: seen.append("dynamodb"))
    monkeypatch.setattr(builder, "_apply_s3_grant", lambda *args: seen.append("s3"))
    monkeypatch.setattr(builder, "_apply_generic_permission", lambda *args: seen.append("generic"))
    method = make_method(decorators=auth("users"))
    builder._apply_permissions(object(), object(), method)
    assert seen == []
