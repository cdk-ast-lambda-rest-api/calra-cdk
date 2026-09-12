from enum import Enum


class ApiType(Enum):
    """The API Gateway family managed by :class:`LambdaApi`."""

    REST = "rest"
    HTTP = "http"
