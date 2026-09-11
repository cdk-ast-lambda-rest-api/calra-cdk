import ast

from lambda_api_decorators_cdk.ast_helper import get_file_nodes


SOURCE = '@GET("/items")\ndef handle(event, context):\n    pass\n'


def test_root_level_file_directory_packaging(tmp_path):
    methods = get_file_nodes(ast.parse(SOURCE), "handler.py", str(tmp_path))[0].get_methods()
    assert methods[0].get_path_to_file() == str(tmp_path)
    assert methods[0].get_file() == "handler.py"
    assert methods[0].get_handler() == "handle"


def test_nested_file_directory_packaging(tmp_path):
    method = get_file_nodes(ast.parse(SOURCE), "nested/handler.py", str(tmp_path))[0].get_methods()[0]
    assert method.get_path_to_file() == str(tmp_path / "nested")
    assert method.get_file() == "handler.py"
    assert method.get_handler() == "handle"


def test_same_basename_in_different_directories_has_same_logical_id(tmp_path):
    ids = [get_file_nodes(ast.parse(SOURCE), f"{folder}/handler.py", str(tmp_path))[0]
           .get_methods()[0].get_logical_id() for folder in ("one", "two")]
    assert ids == ["handlerdotpy-handle", "handlerdotpy-handle"]
