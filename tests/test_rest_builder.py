from conftest import make_graph, make_method
from lambda_api_decorators_cdk import resource_builder as module


class FakeRestResource:
    def __init__(self, path="/"):
        self.path = path
        self.children = []
        self.methods = []

    def add_resource(self, name):
        child = FakeRestResource(self.path.rstrip("/") + "/" + name)
        self.children.append(child)
        return child

    def add_method(self, method, integration):
        self.methods.append((method, integration))


def test_rest_root_methods_and_lambda_integration(builder, monkeypatch):
    lambdas, integrations = [], []
    monkeypatch.setattr(builder, "build_lambda_function", lambda c, m: lambdas.append(m) or f"lambda-{m.method}")
    monkeypatch.setattr(module.apigateway, "LambdaIntegration",
                        lambda value: integrations.append(value) or ("integration", value))
    root = FakeRestResource()
    graph = make_graph(methods=[make_method("GET"), make_method("ANY")])
    builder.build_from_graph(object(), graph, root)
    assert [m[0] for m in root.methods] == ["GET", "ANY"]
    assert integrations == ["lambda-GET", "lambda-ANY"]


def test_rest_creates_intermediate_nested_and_sibling_resources(builder, monkeypatch):
    monkeypatch.setattr(builder, "build_lambda_function", lambda c, m: object())
    monkeypatch.setattr(module.apigateway, "LambdaIntegration", lambda value: value)
    root = make_graph()
    nested = make_graph("/users/{id}/events", [make_method("POST")])
    sibling = make_graph("/users-old", [make_method("DELETE")])
    root.connect(nested)
    root.connect(sibling)
    api = FakeRestResource()
    builder.build_from_graph(object(), root, api)
    assert api.children[0].path == "/users"
    assert api.children[0].children[0].path == "/users/{id}"
    assert api.children[0].children[0].children[0].path == "/users/{id}/events"
    assert api.children[1].path == "/users-old"


def test_multi_route_handler_attempts_duplicate_lambda_construction(builder, monkeypatch):
    calls = []
    monkeypatch.setattr(builder, "build_lambda_function",
                        lambda c, m: calls.append(m.get_logical_id()) or object())
    monkeypatch.setattr(module.apigateway, "LambdaIntegration", lambda value: value)
    graph = make_graph("/items", [make_method("GET"), make_method("POST")])
    builder.build_from_graph(object(), graph, FakeRestResource())
    assert calls == ["handlerdotpy-handle", "handlerdotpy-handle"]
