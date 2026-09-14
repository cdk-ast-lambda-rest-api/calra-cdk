import ast

import pytest

from conftest import decorator_invocations
from lambda_api_decorators_cdk.ast_helper import get_file_nodes


def parse_method(source):
    resources = get_file_nodes(ast.parse(source), "handler.py", "lambdas")
    return resources[0].get_methods()[0]


def test_mixed_decorators_share_one_lexically_ordered_invocation_sequence():
    method = parse_method('''
@GET("/orders")
@runtime("python3.12")
@role("processor")
@grant_dynamodb("orders", "write")
@grant_s3("documents", "read")
@permission(actions=["events:PutEvents"], resources=["arn:example"])
def handler(event, context): pass
''')
    assert decorator_invocations(method) == [
        ("GET", ("/orders",), ()),
        ("runtime", ("python3.12",), ()),
        ("role", ("processor",), ()),
        ("grant_dynamodb", ("orders", "write"), ()),
        ("grant_s3", ("documents", "read"), ()),
        ("permission", (), (
            ("actions", ("events:PutEvents",)),
            ("resources", ("arn:example",)),
        )),
    ]


def test_repeated_configuration_and_permission_decorators_remain_separate():
    method = parse_method('''
@GET("/")
@grant_dynamodb("orders", "read")
@grant_dynamodb("customers", "write")
@layer("base")
@layer("extra")
@environment("FIRST")
@environment("SECOND")
@security_group("web")
@security_group("database")
def handler(event, context): pass
''')
    assert decorator_invocations(method)[1:] == [
        ("grant_dynamodb", ("orders", "read"), ()),
        ("grant_dynamodb", ("customers", "write"), ()),
        ("layer", ("base",), ()),
        ("layer", ("extra",), ()),
        ("environment", ("FIRST",), ()),
        ("environment", ("SECOND",), ()),
        ("security_group", ("web",), ()),
        ("security_group", ("database",), ()),
    ]


@pytest.mark.parametrize("name,path", [
    ("GET", "/orders"),
    ("POST", "/orders"),
    ("PUT", "/orders/{id}"),
    ("DELETE", "/orders/{id}"),
    ("ANY", "/{proxy+}"),
])
def test_each_http_decorator_is_captured_losslessly(name, path):
    method = parse_method(
        f'@{name}("{path}")\ndef handler(event, context): pass\n')
    assert decorator_invocations(method) == [(name, (path,), ())]


def test_all_existing_configuration_decorators_use_the_uniform_model():
    method = parse_method('''
@GET("/")
@runtime("python3.12")
@timeout(30)
@memory_size(512)
@role("worker")
@vpc("private")
@environment("STAGE")
@layer("base")
@security_group("web")
@name("orders")
@description("Orders API")
def handler(event, context): pass
''')
    assert decorator_invocations(method) == [
        ("GET", ("/",), ()),
        ("runtime", ("python3.12",), ()),
        ("timeout", (30,), ()),
        ("memory_size", (512,), ()),
        ("role", ("worker",), ()),
        ("vpc", ("private",), ()),
        ("environment", ("STAGE",), ()),
        ("layer", ("base",), ()),
        ("security_group", ("web",), ()),
        ("name", ("orders",), ()),
        ("description", ("Orders API",), ()),
    ]


def test_literal_values_and_keyword_order_are_preserved_as_python_data():
    method = parse_method('''
@GET("/")
@metadata(
    text="value",
    count=3,
    enabled=True,
    missing=None,
    names=["one", "two"],
    pair=("left", "right"),
    settings={"mode": "strict", "retry": 2},
)
def handler(event, context): pass
''')
    assert decorator_invocations(method)[1] == (
        "metadata", (), (
            ("text", "value"),
            ("count", 3),
            ("enabled", True),
            ("missing", None),
            ("names", ["one", "two"]),
            ("pair", ("left", "right")),
            ("settings", {"mode": "strict", "retry": 2}),
        ),
    )


@pytest.mark.parametrize("decorator,expected", [
    ('grant_dynamodb("orders", "read")', ("grant_dynamodb", ("orders", "read"), ())),
    ('grant_dynamodb("orders", "write")', ("grant_dynamodb", ("orders", "write"), ())),
    ('grant_dynamodb(resource_key="orders", access="read")',
     ("grant_dynamodb", (), (("resource_key", "orders"), ("access", "read")))),
    ('grant_dynamodb(table_name="orders-prod", access="read")',
     ("grant_dynamodb", (), (("table_name", "orders-prod"), ("access", "read")))),
    ('grant_dynamodb(table_name="orders-prod", access="write")',
     ("grant_dynamodb", (), (("table_name", "orders-prod"), ("access", "write")))),
    ('grant_s3("documents", "read")', ("grant_s3", ("documents", "read"), ())),
    ('grant_s3("documents", "write")', ("grant_s3", ("documents", "write"), ())),
    ('grant_s3(resource_key="documents", access="read")',
     ("grant_s3", (), (("resource_key", "documents"), ("access", "read")))),
    ('grant_s3(bucket_name="documents-prod", access="read")',
     ("grant_s3", (), (("bucket_name", "documents-prod"), ("access", "read")))),
    ('grant_s3(bucket_name="documents-prod", access="write")',
     ("grant_s3", (), (("bucket_name", "documents-prod"), ("access", "write")))),
])
def test_semantic_grant_forms_are_captured_losslessly(decorator, expected):
    method = parse_method(
        f'@GET("/")\n@{decorator}\ndef handler(event, context): pass\n')
    assert decorator_invocations(method)[1] == expected


@pytest.mark.parametrize("actions,resources", [
    (
        '["events:PutEvents", "events:DescribeRule"]',
        '["arn:one", "arn:two"]',
    ),
    (
        '("events:PutEvents", "events:DescribeRule")',
        '("arn:one", "arn:two")',
    ),
])
def test_permission_normalizes_actions_and_resources_to_immutable_tuples(
        actions, resources):
    method = parse_method(f'''
@GET("/")
@permission(actions={actions}, resources={resources})
def handler(event, context): pass
''')
    assert decorator_invocations(method)[1] == (
        "permission", (), (
            ("actions", ("events:PutEvents", "events:DescribeRule")),
            ("resources", ("arn:one", "arn:two")),
        ),
    )


@pytest.mark.parametrize("decorator,fragment", [
    ('grant_dynamodb(resource_key="orders", table_name="orders-prod", access="read")', "resource_key"),
    ('grant_dynamodb(access="read")', "resource_key"),
    ('grant_dynamodb(resource_key="", access="read")', "resource_key"),
    ('grant_dynamodb(resource_key="   ", access="read")', "resource_key"),
    ('grant_dynamodb("orders", "read_write")', "access"),
    ('grant_dynamodb(resource_key="orders", access="read", index_name="by-date")', "index_name"),
    ('grant_dynamodb(resource_key="orders", access="read", global_index="by-date")', "global_index"),
    ('grant_dynamodb(resource_key="orders", access="read", local_index="by-date")', "local_index"),
    ('grant_dynamodb(resource_key="orders", access="read", stream_arn="arn:stream")', "stream_arn"),
    ('grant_s3(resource_key="documents", bucket_name="documents-prod", access="read")', "resource_key"),
    ('grant_s3(access="read")', "resource_key"),
    ('grant_s3(bucket_name="", access="read")', "bucket_name"),
    ('grant_s3(bucket_name="   ", access="read")', "bucket_name"),
    ('grant_s3("documents", "read_write")', "access"),
    ('grant_s3(resource_key="documents", access="read", prefix="private/")', "prefix"),
])
def test_malformed_semantic_grants_fail_early_with_context(decorator, fragment):
    with pytest.raises((TypeError, ValueError), match=rf"(?i){fragment}"):
        parse_method(
            f'@GET("/")\n@{decorator}\ndef handler(event, context): pass\n')


@pytest.mark.parametrize("decorator,fragment", [
    ('permission(resources=["arn:one"])', "actions"),
    ('permission(actions=["events:PutEvents"])', "resources"),
    ('permission(["events:PutEvents"], ["arn:one"])', "permission"),
    ('permission(actions=[], resources=["arn:one"])', "actions"),
    ('permission(actions=["events:PutEvents"], resources=[])', "resources"),
    ('permission(actions=[1], resources=["arn:one"])', "actions"),
    ('permission(actions=["events:PutEvents"], resources=[1])', "resources"),
    ('permission(actions=["events:PutEvents"], resources=["arn:one"], effect="Allow")', "effect"),
    ('permission(actions=["events:PutEvents"], resources=["arn:one"], conditions={})', "conditions"),
    ('permission(actions=["events:PutEvents"], resources=["arn:one"], principals=["*"])', "principals"),
    ('permission(actions=["events:PutEvents"], resources=["arn:one"], not_actions=[])', "not_actions"),
    ('permission(actions=["events:PutEvents"], resources=["arn:one"], not_resources=[])', "not_resources"),
    ('permission(actions=["events:PutEvents"], resources=["arn:one"], sid="Statement")', "sid"),
])
def test_malformed_permission_fails_early_with_context(decorator, fragment):
    with pytest.raises((TypeError, ValueError), match=rf"(?i){fragment}"):
        parse_method(
            f'@GET("/")\n@{decorator}\ndef handler(event, context): pass\n')


@pytest.mark.parametrize("expression", [
    "TABLE_NAME",
    "get_table_name()",
    'f"{prefix}-orders"',
    "SomeClass.VALUE",
])
def test_supported_decorators_reject_dynamic_expressions(expression):
    with pytest.raises((TypeError, ValueError), match="(?i)grant_dynamodb"):
        parse_method(f'''
@GET("/")
@grant_dynamodb(table_name={expression}, access="read")
def handler(event, context): pass
''')


def test_unknown_called_decorator_is_captured_but_not_interpreted_by_ast_layer():
    method = parse_method('''
@GET("/")
@application_metadata("value", enabled=True)
def handler(event, context): pass
''')
    assert decorator_invocations(method)[1] == (
        "application_metadata", ("value",), (("enabled", True),))
