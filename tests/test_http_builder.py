import pytest

from conftest import make_graph, make_method
from lambda_api_decorators_cdk import resource_builder as module


class FakeHttpApi:
    def __init__(self):
        self.routes = []

    def add_routes(self, **kwargs):
        self.routes.append(kwargs)


@pytest.mark.parametrize("verb", ["GET", "POST", "PUT", "DELETE"])
@pytest.mark.parametrize("path", ["/", "/users/{id}"])
def test_http_routes_supported_methods_at_full_path(builder, monkeypatch, verb, path):
    monkeypatch.setattr(builder, "build_lambda_function", lambda c, m: "lambda")
    monkeypatch.setattr(module.integrations, "HttpLambdaIntegration", lambda i, l: (i, l))
    api = FakeHttpApi()
    builder.build_http_from_graph(object(), make_graph(path, [make_method(verb)]), api)
    assert api.routes[0]["path"] == path
    assert api.routes[0]["methods"] == [getattr(module.apigateway2.HttpMethod, verb)]
    assert api.routes[0]["integration"][1] == "lambda"


def test_http_any_currently_raises_key_error(builder, monkeypatch):
    monkeypatch.setattr(builder, "build_lambda_function", lambda c, m: object())
    monkeypatch.setattr(module.integrations, "HttpLambdaIntegration", lambda i, l: object())
    with pytest.raises(KeyError, match="ANY"):
        builder.build_http_from_graph(object(), make_graph("/", [make_method("ANY")]), FakeHttpApi())


def test_http_integration_id_uses_method_logical_id_value(builder, monkeypatch):
    """EXPECTED BEHAVIOR / BUG REGRESSION: current f-string uses bound method."""
    ids = []
    monkeypatch.setattr(builder, "build_lambda_function", lambda c, m: object())
    monkeypatch.setattr(module.integrations, "HttpLambdaIntegration",
                        lambda integration_id, function: ids.append(integration_id) or object())
    builder.build_http_from_graph(object(), make_graph("/", [make_method()]), FakeHttpApi())
    assert ids == ["handlerdotpy-handleApiLambdaIntegration"]


def test_http_traverses_siblings_and_nested_connections(builder, monkeypatch):
    monkeypatch.setattr(builder, "build_lambda_function", lambda c, m: object())
    monkeypatch.setattr(module.integrations, "HttpLambdaIntegration", lambda i, l: object())
    root = make_graph()
    users = make_graph("/users", [make_method("GET")])
    users.connect(make_graph("/users/{id}", [make_method("PUT")]))
    root.connect(users)
    root.connect(make_graph("/users-old", [make_method("DELETE")]))
    api = FakeHttpApi()
    builder.build_http_from_graph(object(), root, api)
    assert [route["path"] for route in api.routes] == ["/users", "/users/{id}", "/users-old"]
