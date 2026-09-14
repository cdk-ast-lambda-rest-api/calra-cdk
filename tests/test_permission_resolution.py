"""Block 4T4 contracts for applying permission decorators to Lambda roles.

These tests intentionally describe the next implementation block.  Registry
storage is already supported; resolving grants and mutating roles is not.
"""

import ast

import pytest
from aws_cdk import App, Stack
from aws_cdk import assertions
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as s3

from lambda_api_decorators_cdk import LambdaApi, LambdaApiConfig, ResourceBuilder
from lambda_api_decorators_cdk import ast_helper
from lambda_api_decorators_cdk import resource_builder as builder_module


def permission_method(*decorators, file="handler.py", handler="handle"):
    source = "\n".join(
        ['@GET("/")', *[f"@{decorator}" for decorator in decorators],
         f"def {handler}(event, context): pass"]
    )
    return ast_helper.get_file_nodes(
        ast.parse(source), file, "lambdas"
    )[0].get_methods()[0]


def install_inline_lambda(monkeypatch):
    """Replace Python bundling with a normal inline Lambda CDK construct."""
    created = []

    def create(scope, construct_id, **options):
        function = lambda_.Function(
            scope,
            construct_id,
            runtime=options.get("runtime") or lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                "def handler(event, context):\n    return {'statusCode': 200}\n"
            ),
            role=options.get("role"),
        )
        created.append(function)
        return function

    monkeypatch.setattr(builder_module._lambda_python, "PythonFunction", create)
    return created


def synthesized(stack):
    return assertions.Template.from_stack(stack).to_json()


def policy_statements(stack):
    resources = synthesized(stack).get("Resources", {})
    statements = []
    for resource in resources.values():
        if resource["Type"] in ("AWS::IAM::Policy", "AWS::IAM::Role"):
            properties = resource.get("Properties", {})
            documents = []
            if "PolicyDocument" in properties:
                documents.append(properties["PolicyDocument"])
            documents.extend(
                policy["PolicyDocument"] for policy in properties.get("Policies", [])
            )
            for document in documents:
                statements.extend(document.get("Statement", []))
    return statements


def actions(stack):
    result = set()
    for statement in policy_statements(stack):
        value = statement.get("Action", [])
        result.update([value] if isinstance(value, str) else value)
    return result


def flattened_resources(stack):
    return str([statement.get("Resource") for statement in policy_statements(stack)])


def has_resolved_resource(stack, resource_arn):
    """Match a CDK ARN token against its synthesized CloudFormation value."""
    expected = stack.resolve(resource_arn)
    for statement in policy_statements(stack):
        resources = statement.get("Resource", [])
        if not isinstance(resources, list):
            resources = [resources]
        if expected in resources:
            return True
    return False


@pytest.fixture
def stack():
    return Stack(App(), "Stack")


@pytest.fixture
def inline_lambdas(monkeypatch):
    return install_inline_lambda(monkeypatch)


@pytest.fixture
def table(stack):
    return dynamodb.Table(
        stack, "Orders", partition_key=dynamodb.Attribute(
            name="id", type=dynamodb.AttributeType.STRING
        )
    )


@pytest.fixture
def bucket(stack):
    return s3.Bucket(stack, "Documents")


@pytest.mark.parametrize("form", [
    'grant_dynamodb("orders", "read")',
    'grant_dynamodb(resource_key="orders", access="read")',
])
def test_dynamodb_logical_key_resolves_registered_resource(
    stack, inline_lambdas, table, form
):
    builder = ResourceBuilder(dynamodb_tables={"orders": table})
    builder.build_lambda_function(stack, permission_method(form))
    assert "dynamodb:GetItem" in actions(stack)
    assert has_resolved_resource(stack, table.table_arn)


def test_missing_dynamodb_logical_key_fails_with_decorator_context(stack, inline_lambdas):
    builder = ResourceBuilder()
    with pytest.raises(KeyError, match="(?i)dynamodb.*missing"):
        builder.build_lambda_function(
            stack, permission_method('grant_dynamodb("missing", "read")')
        )


@pytest.mark.parametrize("access,required", [
    ("read", {"dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"}),
    ("write", {"dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"}),
])
def test_dynamodb_access_maps_to_native_read_or_read_write_grant(
    stack, inline_lambdas, table, access, required
):
    ResourceBuilder(dynamodb_tables={"orders": table}).build_lambda_function(
        stack, permission_method(f'grant_dynamodb("orders", "{access}")')
    )
    assert required <= actions(stack)


def test_dynamodb_physical_name_grants_table_and_index_resources(stack, inline_lambdas):
    ResourceBuilder().build_lambda_function(
        stack,
        permission_method(
            'grant_dynamodb(table_name="orders-production", access="read")'
        ),
    )
    resources = flattened_resources(stack)
    assert "table/orders-production" in resources
    assert "table/orders-production/index/" in resources
    assert "dynamodb:Query" in actions(stack)


def test_dynamodb_physical_resource_is_reused_without_construct_collision(
    stack, inline_lambdas
):
    builder = ResourceBuilder()
    for file, handler in (("first.py", "first"), ("second.py", "second")):
        builder.build_lambda_function(
            stack,
            permission_method(
                'grant_dynamodb(table_name="orders-production", access="read")',
                file=file,
                handler=handler,
            ),
        )
    assert len(synthesized(stack)["Resources"]) >= 4
    assert flattened_resources(stack).count("table/orders-production") >= 2


@pytest.mark.parametrize("form", [
    'grant_s3("documents", "read")',
    'grant_s3(resource_key="documents", access="read")',
])
def test_s3_logical_key_resolves_registered_resource(
    stack, inline_lambdas, bucket, form
):
    ResourceBuilder(s3_buckets={"documents": bucket}).build_lambda_function(
        stack, permission_method(form)
    )
    assert {"s3:GetObject*", "s3:GetBucket*", "s3:List*"} <= actions(stack)
    assert has_resolved_resource(stack, bucket.bucket_arn)


def test_missing_s3_logical_key_fails_with_decorator_context(stack, inline_lambdas):
    with pytest.raises(KeyError, match="(?i)s3.*missing"):
        ResourceBuilder().build_lambda_function(
            stack, permission_method('grant_s3("missing", "read")')
        )


@pytest.mark.parametrize("access,required", [
    ("read", {"s3:GetObject*", "s3:GetBucket*", "s3:List*"}),
    ("write", {
        "s3:GetObject*", "s3:GetBucket*", "s3:List*",
        "s3:DeleteObject*", "s3:PutObject",
    }),
])
def test_s3_access_maps_to_native_read_or_read_write_grant(
    stack, inline_lambdas, bucket, access, required
):
    ResourceBuilder(s3_buckets={"documents": bucket}).build_lambda_function(
        stack, permission_method(f'grant_s3("documents", "{access}")')
    )
    assert required <= actions(stack)


def test_s3_physical_name_resolves_and_grants_bucket(stack, inline_lambdas):
    ResourceBuilder().build_lambda_function(
        stack,
        permission_method(
            'grant_s3(bucket_name="documents-production", access="read")'
        ),
    )
    assert "documents-production" in flattened_resources(stack)
    assert {"s3:GetObject*", "s3:GetBucket*", "s3:List*"} <= actions(stack)


def test_s3_physical_resource_is_reused_without_construct_collision(stack, inline_lambdas):
    builder = ResourceBuilder()
    for file, handler in (("first.py", "first"), ("second.py", "second")):
        builder.build_lambda_function(
            stack,
            permission_method(
                'grant_s3(bucket_name="documents-production", access="read")',
                file=file,
                handler=handler,
            ),
        )
    assert len(synthesized(stack)["Resources"]) >= 4
    assert flattened_resources(stack).count("documents-production") >= 2


def test_generic_permission_adds_iam_statement_to_function_role(stack, inline_lambdas):
    ResourceBuilder().build_lambda_function(
        stack,
        permission_method(
            'permission(actions=["events:PutEvents"], '
            'resources=["arn:aws:events:us-east-1:123456789012:event-bus/orders"])'
        ),
    )
    assert "events:PutEvents" in actions(stack)
    assert "event-bus/orders" in flattened_resources(stack)


def test_repeated_permissions_are_all_applied(stack, inline_lambdas):
    ResourceBuilder().build_lambda_function(
        stack,
        permission_method(
            'permission(actions=["events:PutEvents"], resources=["arn:events"])',
            'permission(actions=["sns:Publish"], resources=["arn:sns"])',
        ),
    )
    assert {"events:PutEvents", "sns:Publish"} <= actions(stack)


def test_mixed_grants_and_generic_permissions_are_all_applied(
    stack, inline_lambdas, table, bucket
):
    ResourceBuilder(
        dynamodb_tables={"orders": table}, s3_buckets={"documents": bucket}
    ).build_lambda_function(
        stack,
        permission_method(
            'grant_dynamodb("orders", "read")',
            'permission(actions=["events:PutEvents"], resources=["arn:events"])',
            'grant_s3("documents", "write")',
        ),
    )
    assert {"dynamodb:GetItem", "s3:PutObject", "events:PutEvents"} <= actions(stack)


@pytest.mark.parametrize("role_source", ["explicit", "default", "generated"])
def test_permissions_attach_to_the_role_selected_for_the_lambda_lifecycle(
    stack, inline_lambdas, role_source
):
    builder = ResourceBuilder()
    decorator = None
    selected_role = None
    if role_source != "generated":
        selected_role = iam.Role(
            stack, f"{role_source.title()}Role", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )
    if role_source == "explicit":
        builder.add_custom_role("worker", selected_role)
        decorator = 'role("worker")'
    elif role_source == "default":
        builder.set_default_role(selected_role)

    decorators = [
        'permission(actions=["events:PutEvents"], resources=["arn:events"])'
    ]
    if decorator:
        decorators.insert(0, decorator)
    function = builder.build_lambda_function(stack, permission_method(*decorators))

    assert "events:PutEvents" in actions(stack)
    if selected_role is not None:
        assert function.role.role_arn == selected_role.role_arn
    else:
        assert function.role is not None


def test_permissions_are_applied_after_function_creation_and_exactly_once(monkeypatch):
    events = []

    class TableSpy:
        def grant_read_data(self, grantee):
            events.append(("grant", grantee))

    function = object()

    def create(*args, **kwargs):
        events.append(("create", function))
        return function

    monkeypatch.setattr(builder_module._lambda_python, "PythonFunction", create)
    ResourceBuilder(dynamodb_tables={"orders": TableSpy()}).build_lambda_function(
        object(), permission_method('grant_dynamodb("orders", "read")')
    )
    assert events == [("create", function), ("grant", function)]


def test_lambda_api_high_level_config_applies_registered_grants(
    stack, monkeypatch, table
):
    install_inline_lambda(monkeypatch)
    graph = ast_helper.Resource("/")
    graph.add_method(permission_method('grant_dynamodb("orders", "read")'))
    monkeypatch.setattr(ast_helper, "get_lambda_graph", lambda _path: graph)

    LambdaApi(
        stack,
        "Api",
        lambda_path="lambdas",
        config=LambdaApiConfig(dynamodb_tables={"orders": table}),
    )

    assert "dynamodb:GetItem" in actions(stack)
    assert has_resolved_resource(stack, table.table_arn)
