from aws_cdk import App, Stack, aws_apigateway as apigateway
from aws_cdk import aws_apigatewayv2_authorizers as http_authorizers
from aws_cdk import aws_cognito as cognito, aws_lambda as lambda_
from aws_cdk.assertions import Annotations, Match, Template

from lambda_api_decorators_cdk import ApiType, LambdaApi, LambdaApiConfig, ResourceBuilder


def write_handler(tmp_path, auth):
    root = tmp_path / "handlers"
    root.mkdir()
    (root / "handler.py").write_text(
        f'@GET("/me")\n{auth}\ndef handler(event, context): pass\n'
    )
    return str(root)


def patch_lambda_build(monkeypatch):
    def build(self, construct, method, *args, **kwargs):
        return lambda_.Function(
            construct,
            method.get_logical_id(),
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline("def handler(event, context): return {}"),
        )

    monkeypatch.setattr(ResourceBuilder, "build_lambda_function", build)


def test_high_level_rest_config_reaches_synthesized_protected_method(tmp_path, monkeypatch):
    stack = Stack(App(), "Stack")
    pool = cognito.UserPool(stack, "Pool")
    resolved = apigateway.CognitoUserPoolsAuthorizer(
        stack, "Users", cognito_user_pools=[pool]
    )
    config = LambdaApiConfig(authorizers={"users": resolved}, default_authorizer=None)
    patch_lambda_build(monkeypatch)
    LambdaApi(
        stack,
        "Api",
        lambda_path=write_handler(tmp_path, '@authorizer("users")'),
        config=config,
    )
    Template.from_stack(stack).has_resource_properties(
        "AWS::ApiGateway::Method",
        {"HttpMethod": "GET", "AuthorizationType": "COGNITO_USER_POOLS", "AuthorizerId": Match.any_value()},
    )
    warnings = Annotations.from_stack(stack).find_warning(
        "/Stack/Api", Match.string_like_regexp("LAD_AUTH_PUBLIC_DEFAULT")
    )
    assert len(warnings) == 1


def test_high_level_http_config_reaches_synthesized_protected_route(tmp_path, monkeypatch):
    stack = Stack(App(), "Stack")
    resolved = http_authorizers.HttpJwtAuthorizer(
        "Users", "https://issuer.example", jwt_audience=["audience"]
    )
    config = LambdaApiConfig(authorizers={"users": resolved}, default_authorizer="users")
    patch_lambda_build(monkeypatch)
    LambdaApi(
        stack,
        "Api",
        lambda_path=write_handler(tmp_path, '@authorizer("users")'),
        api_type=ApiType.HTTP,
        config=config,
    )
    Template.from_stack(stack).has_resource_properties(
        "AWS::ApiGatewayV2::Route",
        {"RouteKey": "GET /me", "AuthorizationType": "JWT", "AuthorizerId": Match.any_value()},
    )
