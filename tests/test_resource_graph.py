from conftest import make_method
from lambda_api_decorators_cdk.ast_helper import Method, Resource


def test_method_accessors_and_logical_id():
    method = make_method(file="nested/handler.py", handler="run", decorators={"x": 1})
    assert method.get_logical_id() == "nested-handlerdotpy-run"
    assert method.get_file() == "nested/handler.py"
    assert method.get_path_to_file() == "lambdas"
    assert method.get_handler() == "run"
    assert method.get_method() == "GET"
    assert method.get_decorators() == {"x": 1}


def test_method_equality_currently_returns_false_for_equivalent_methods():
    left, right = make_method(), make_method()
    assert (left == right) is False
    import pytest
    with pytest.raises(AttributeError):
        left == object()


def test_resource_adds_multiple_methods_and_merges_same_path():
    resource = Resource("/items")
    get, post = make_method("GET"), make_method("POST")
    assert resource.add_method(get) is True
    assert resource.add_method(post) is True
    other = Resource("/items")
    other.add_method(make_method("DELETE"))
    assert resource.insert_node(other) is True
    assert [m.get_method() for m in resource.get_methods()] == ["GET", "POST", "DELETE"]


def test_equivalent_duplicate_method_is_retained_due_to_current_equality():
    resource = Resource("/items")
    assert resource.add_method(make_method()) is True
    assert resource.add_method(make_method()) is True
    assert len(resource.get_methods()) == 2


def test_resource_add_methods_currently_does_nothing_for_empty_resource():
    resource = Resource("/items")
    assert resource.add_methods([make_method()]) is None
    assert resource.get_methods() == []


def test_nested_sibling_and_common_text_prefix_resources():
    root = Resource("/")
    users = Resource("/users")
    nested = Resource("/users/{id}")
    old = Resource("/users-old")
    for resource in (users, nested, old):
        assert root.insert_node(resource) is True
    assert [r.get_path() for r in root.get_connections()] == ["/users", "/users-old"]
    assert [r.get_path() for r in users.get_connections()] == ["/users/{id}"]


def test_method_rejects_unsupported_http_method():
    import pytest
    with pytest.raises(ValueError, match="Invalid method"):
        Method(".", "handler.py", "handle", "PATCH", {})
