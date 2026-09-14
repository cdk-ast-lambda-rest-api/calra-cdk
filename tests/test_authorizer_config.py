import inspect

import pytest
from aws_cdk import App, Stack, aws_apigateway as apigateway
from aws_cdk import aws_apigatewayv2_authorizers as http_authorizers
from aws_cdk import aws_cognito as cognito

from lambda_api_decorators_cdk import LambdaApiConfig


@pytest.fixture
def authorizers():
    stack = Stack(App(), "AuthorizerStack")
    pool = cognito.UserPool(stack, "Pool")
    return {
        "rest": apigateway.CognitoUserPoolsAuthorizer(
            stack, "RestAuthorizer", cognito_user_pools=[pool]
        ),
        "http": http_authorizers.HttpJwtAuthorizer(
            "HttpAuthorizer", "https://issuer.example", jwt_audience=["audience"]
        ),
    }


def test_authorizer_constructor_parameters_are_keyword_only():
    parameters = inspect.signature(LambdaApiConfig).parameters
    assert parameters["authorizers"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["authorizers"].default is None
    assert parameters["default_authorizer"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["default_authorizer"].default is None


def test_constructor_registers_both_authorizer_families_before_default(authorizers):
    config = LambdaApiConfig(
        authorizers={"users": authorizers["rest"], "jwt": authorizers["http"]},
        default_authorizer="users",
    )
    builder = config._create_resource_builder()
    assert builder.authorizers == {
        "users": authorizers["rest"],
        "jwt": authorizers["http"],
    }
    assert builder.default_authorizer == "users"


@pytest.mark.parametrize("key,error", [(None, TypeError), (1, TypeError), ("", ValueError), ("  ", ValueError)])
def test_authorizer_registry_rejects_invalid_keys(authorizers, key, error):
    with pytest.raises(error):
        LambdaApiConfig(authorizers={key: authorizers["rest"]})


@pytest.mark.parametrize("value", [None, "authorizer", 1, object()])
def test_authorizer_registry_rejects_obviously_invalid_values(value):
    with pytest.raises(TypeError, match="(?i)authorizer"):
        LambdaApiConfig(authorizers={"users": value})


def test_add_authorizer_preserves_key_and_identity_and_returns_none(authorizers):
    config = LambdaApiConfig()
    assert config.add_authorizer(" users ", authorizers["rest"]) is None
    builder = config._create_resource_builder()
    assert list(builder.authorizers) == [" users "]
    assert builder.authorizers[" users "] is authorizers["rest"]


def test_duplicate_authorizer_registration_is_rejected_without_overwrite(authorizers):
    config = LambdaApiConfig(authorizers={"users": authorizers["rest"]})
    with pytest.raises(ValueError, match="users"):
        config.add_authorizer("users", authorizers["http"])
    assert config._create_resource_builder().authorizers["users"] is authorizers["rest"]


@pytest.mark.parametrize(
    "default,error",
    [(1, TypeError), (object(), TypeError), ("", ValueError), ("   ", ValueError)],
)
def test_default_authorizer_rejects_invalid_keys(default, error):
    with pytest.raises(error):
        LambdaApiConfig(default_authorizer=default)


def test_default_authorizer_must_already_be_registered(authorizers):
    with pytest.raises((KeyError, ValueError), match="missing"):
        LambdaApiConfig(authorizers={"users": authorizers["rest"]}, default_authorizer="missing")


def test_default_authorizer_can_be_set_and_cleared(authorizers):
    config = LambdaApiConfig(authorizers={"users": authorizers["rest"]})
    assert config.set_default_authorizer("users") is None
    assert config._create_resource_builder().default_authorizer == "users"
    assert config.set_default_authorizer(None) is None
    assert config._create_resource_builder().default_authorizer is None


def test_set_default_authorizer_requires_an_exact_registered_key(authorizers):
    config = LambdaApiConfig(authorizers={" users ": authorizers["rest"]})
    with pytest.raises((KeyError, ValueError), match="users"):
        config.set_default_authorizer("users")


def test_authorizer_registry_snapshots_are_shallow_and_isolated(authorizers):
    supplied = {"users": authorizers["rest"]}
    config = LambdaApiConfig(authorizers=supplied, default_authorizer="users")
    supplied.clear()
    first = config._create_resource_builder()
    config.add_authorizer("jwt", authorizers["http"])
    second = config._create_resource_builder()
    assert first.authorizers == {"users": authorizers["rest"]}
    assert set(second.authorizers) == {"users", "jwt"}
    assert first.authorizers is not second.authorizers
    assert first.authorizers["users"] is second.authorizers["users"]
    first.authorizers.clear()
    assert set(config._create_resource_builder().authorizers) == {"users", "jwt"}
