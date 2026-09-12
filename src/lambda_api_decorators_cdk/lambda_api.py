from typing import Optional, Union

from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_apigatewayv2 as apigatewayv2
from constructs import Construct

from .api_type import ApiType
from .lambda_api_config import LambdaApiConfig


class LambdaApi(Construct):
    """Build decorated Lambda handlers behind an API Gateway."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        lambda_path: str,
        api: Optional[
            Union[apigateway.IRestApi, apigatewayv2.HttpApi]
        ] = None,
        api_type: Optional[ApiType] = None,
        config: Optional[LambdaApiConfig] = None,
    ) -> None:
        super().__init__(scope, construct_id)

        if config is not None and not isinstance(config, LambdaApiConfig):
            raise TypeError("config must be a LambdaApiConfig or None")
        if api_type is not None and not isinstance(api_type, ApiType):
            raise TypeError("api_type must be an ApiType or None")

        inferred_type = self._infer_api_type(api) if api is not None else None
        if api_type is not None and inferred_type is not None and api_type is not inferred_type:
            raise ValueError(
                f"api_type {api_type!r} conflicts with supplied {inferred_type.value} API"
            )

        resolved_type = inferred_type or api_type or ApiType.REST
        resolved_config = config if config is not None else LambdaApiConfig()

        if api is None:
            if resolved_type is ApiType.REST:
                api = apigateway.RestApi(self, "RestApi")
            else:
                api = apigatewayv2.HttpApi(self, "HttpApi")

        self._api = api
        self._api_type = resolved_type
        resource_builder = resolved_config._create_resource_builder()

        if resolved_type is ApiType.REST:
            resource_builder.build(self, api.root, lambda_path)
        else:
            resource_builder.build_http(self, api, lambda_path)

    @staticmethod
    def _infer_api_type(api: object) -> ApiType:
        # IRestApi is a non-runtime-checkable Protocol in CDK Python. Both
        # created and imported REST APIs derive from its concrete RestApiBase.
        if isinstance(api, apigateway.RestApiBase):
            return ApiType.REST
        if isinstance(api, apigatewayv2.HttpApi):
            return ApiType.HTTP
        raise TypeError(
            "api must be an apigateway IRestApi implementation or "
            "apigatewayv2.HttpApi"
        )

    @property
    def api(self) -> Union[apigateway.IRestApi, apigatewayv2.HttpApi]:
        return self._api

    @property
    def api_type(self) -> ApiType:
        return self._api_type
