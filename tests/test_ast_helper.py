import ast

from lambda_api_decorators_cdk.ast_helper import get_file_nodes


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
