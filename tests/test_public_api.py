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


def test_source_layout_is_exported_from_package_and_direct_module():
    from lambda_api_decorators_cdk import SourceLayout
    from lambda_api_decorators_cdk.source_layout import (
        SourceLayout as DirectSourceLayout,
    )

    assert SourceLayout is DirectSourceLayout


def test_source_layout_is_a_non_string_enum_with_exact_stable_members():
    from lambda_api_decorators_cdk import SourceLayout

    assert issubclass(SourceLayout, Enum)
    assert not issubclass(SourceLayout, str)
    assert {member.name: member.value for member in SourceLayout} == {
        "ROOT": "root",
        "SERVICE": "service",
    }
