import ast

import pytest

from lambda_api_decorators_cdk.ast_helper import get_file_nodes, get_lambda_graph


def test_discovers_http_decorators_imported_from_companion_package():
    tree = ast.parse(
        '''
from lambda_api_decorators import DELETE, GET, POST, PUT

@GET("/items")
def list_items(event, context):
    pass

@POST("/items")
@PUT("/items/{item_id}")
@DELETE("/items/{item_id}/archive")
def mutate_item(event, context):
    pass
'''
    )

    resources = get_file_nodes(tree, "handlers.py", "lambdas")

    discovered = {
        (resource.get_path(), method.get_method(), method.get_handler())
        for resource in resources
        for method in resource.get_methods()
    }
    assert discovered == {
        ("/items", "GET", "list_items"),
        ("/items", "POST", "mutate_item"),
        ("/items/{item_id}", "PUT", "mutate_item"),
        ("/items/{item_id}/archive", "DELETE", "mutate_item"),
    }


@pytest.mark.parametrize("verb", ["GET", "POST", "PUT", "DELETE", "ANY"])
def test_discovers_each_supported_http_decorator(verb):
    resources = get_file_nodes(ast.parse(
        f'@{verb}("/route")\ndef handle(event, context):\n    pass\n'),
        "handler.py", "lambdas")
    method = resources[0].get_methods()[0]
    assert (resources[0].get_path(), method.get_method()) == ("/route", verb)


def test_parses_supported_decorator_argument_forms_and_repetitions():
    tree = ast.parse('''
@GET("/")
@runtime("python3.12")
@timeout(30)
@memory_size(512)
@role("worker")
@vpc("private")
@layer(["base", "data"])
@layer("extra")
@security_group("one", "two")
@environment("A", "B")
@name("named")
@description("described")
def handle(event, context):
    pass
''')
    method = get_file_nodes(tree, "handler.py", "lambdas")[0].get_methods()[0]
    assert method.get_decorators() == {
        "runtime": "python3.12", "timeout": 30, "memory_size": 512,
        "role": "worker", "vpc": "private", "layer": ["base", "data", "extra"],
        "security_group": ["one", "two"], "environment": ["A", "B"],
        "name": "named", "description": "described",
    }


def test_multiple_http_decorators_create_multiple_method_records_for_handler():
    resources = get_file_nodes(ast.parse('''
@GET("/items")
@POST("/items")
def handle(event, context): pass
'''), "handler.py", "lambdas")
    methods = resources[0].get_methods()
    assert [(m.get_method(), m.get_handler(), m.get_logical_id()) for m in methods] == [
        ("GET", "handle", "handlerdotpy-handle"),
        ("POST", "handle", "handlerdotpy-handle"),
    ]


def test_decorated_non_http_and_plain_files_create_no_routes(tmp_path, capsys):
    (tmp_path / "decorated.py").write_text('@runtime("x")\ndef helper(): pass\n')
    (tmp_path / "plain.py").write_text('def helper(): pass\n')
    graph = get_lambda_graph(str(tmp_path))
    assert graph.get_methods() == []
    assert graph.get_connections() == []
    assert "Skipped" in capsys.readouterr().out


def test_tree_discovers_root_nested_sibling_and_multiple_files(tmp_path):
    (tmp_path / "one.py").write_text('@GET("/")\ndef root(e,c): pass\n@GET("/users")\ndef users(e,c): pass\n')
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "two.py").write_text('@POST("/users/{id}")\ndef item(e,c): pass\n@DELETE("/users-old")\ndef old(e,c): pass\n')
    graph = get_lambda_graph(str(tmp_path))
    assert [(m.get_method(), m.get_handler()) for m in graph.get_methods()] == [("GET", "root")]
    assert {r.get_path() for r in graph.get_connections()} == {"/users", "/users-old"}
    users = next(r for r in graph.get_connections() if r.get_path() == "/users")
    assert users.get_connections()[0].get_path() == "/users/{id}"


def test_ast_constant_s_characterization_for_strings_numbers_and_lists():
    method = get_file_nodes(ast.parse('''
@GET("/strings")
@description("text")
@timeout(3)
@layer(["one", "two"])
def handler(e, c): pass
'''), "source.py", "root")[0].get_methods()[0]
    assert method.get_decorators() == {"description": "text", "timeout": 3,
                                        "layer": ["one", "two"]}
