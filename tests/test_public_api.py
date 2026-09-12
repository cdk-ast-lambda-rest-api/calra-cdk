from enum import Enum

from lambda_api_decorators_cdk import (
    ApiType,
    LambdaApi,
    LambdaApiConfig,
    ResourceBuilder,
)
from lambda_api_decorators_cdk.api_type import ApiType as DirectApiType
from lambda_api_decorators_cdk.lambda_api import LambdaApi as DirectLambdaApi
from lambda_api_decorators_cdk.lambda_api_config import (
    LambdaApiConfig as DirectLambdaApiConfig,
)
from lambda_api_decorators_cdk.resource_builder import (
    ResourceBuilder as DirectResourceBuilder,
)


def test_public_exports_have_direct_module_identity():
    assert ApiType is DirectApiType
    assert LambdaApi is DirectLambdaApi
    assert LambdaApiConfig is DirectLambdaApiConfig
    assert ResourceBuilder is DirectResourceBuilder


def test_api_type_is_enum_with_stable_values():
    assert issubclass(ApiType, Enum)
    assert ApiType.REST.value == "rest"
    assert ApiType.HTTP.value == "http"
