import ast

from lambda_api_decorators_cdk.ast_helper import get_file_nodes


SOURCE = '@GET("/items")\ndef handle(event, context):\n    pass\n'


def test_same_basename_in_different_directories_has_same_logical_id(tmp_path):
    ids = [get_file_nodes(ast.parse(SOURCE), f"{folder}/handler.py", str(tmp_path))[0]
           .get_methods()[0].get_logical_id() for folder in ("one", "two")]
    assert ids == ["handlerdotpy-handle", "handlerdotpy-handle"]
