import inspect

import pytest
from aws_cdk import Stack, aws_dynamodb as dynamodb, aws_s3 as s3

from lambda_api_decorators_cdk import LambdaApiConfig, ResourceBuilder


@pytest.fixture
def resources():
    stack = Stack()
    return {
        "table": dynamodb.Table.from_table_arn(
            stack,
            "OrdersTable",
            "arn:aws:dynamodb:us-east-1:123456789012:table/orders",
        ),
        "other_table": dynamodb.Table.from_table_arn(
            stack,
            "CustomersTable",
            "arn:aws:dynamodb:us-east-1:123456789012:table/customers",
        ),
        "bucket": s3.Bucket.from_bucket_name(stack, "DocumentsBucket", "documents"),
        "other_bucket": s3.Bucket.from_bucket_name(
            stack, "ArchiveBucket", "documents-archive"
        ),
    }


def test_resource_registry_constructor_parameters_are_keyword_only():
    parameters = inspect.signature(LambdaApiConfig).parameters
    assert parameters["dynamodb_tables"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["dynamodb_tables"].default is None
    assert parameters["s3_buckets"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["s3_buckets"].default is None


def test_constructor_registers_resources_in_separate_typed_registries(resources):
    config = LambdaApiConfig(
        dynamodb_tables={"shared": resources["table"]},
        s3_buckets={"shared": resources["bucket"]},
    )

    builder = config._create_resource_builder()

    assert builder.dynamodb_tables == {"shared": resources["table"]}
    assert builder.s3_buckets == {"shared": resources["bucket"]}
    assert builder.dynamodb_tables["shared"] is resources["table"]
    assert builder.s3_buckets["shared"] is resources["bucket"]


@pytest.mark.parametrize(
    ("method", "resource_name", "registry_name"),
    [
        ("add_dynamodb_table", "table", "dynamodb_tables"),
        ("add_s3_bucket", "bucket", "s3_buckets"),
    ],
)
def test_resource_registry_mutators_return_none_and_preserve_identity(
    resources, method, resource_name, registry_name
):
    config = LambdaApiConfig()
    resource = resources[resource_name]

    assert getattr(config, method)("primary", resource) is None
    assert getattr(config._create_resource_builder(), registry_name)["primary"] is resource


@pytest.mark.parametrize("method", ["add_dynamodb_table", "add_s3_bucket"])
@pytest.mark.parametrize("key", [None, 123])
def test_resource_registry_mutators_reject_non_string_keys(resources, method, key):
    resource = resources["table" if method == "add_dynamodb_table" else "bucket"]
    with pytest.raises(TypeError):
        getattr(LambdaApiConfig(), method)(key, resource)


@pytest.mark.parametrize("method", ["add_dynamodb_table", "add_s3_bucket"])
@pytest.mark.parametrize("key", ["", "   "])
def test_resource_registry_mutators_reject_blank_keys(resources, method, key):
    resource = resources["table" if method == "add_dynamodb_table" else "bucket"]
    with pytest.raises(ValueError):
        getattr(LambdaApiConfig(), method)(key, resource)


@pytest.mark.parametrize(
    ("constructor_name", "resource_name", "invalid_key", "error"),
    [
        ("dynamodb_tables", "table", None, TypeError),
        ("dynamodb_tables", "table", 123, TypeError),
        ("dynamodb_tables", "table", "", ValueError),
        ("dynamodb_tables", "table", "   ", ValueError),
        ("s3_buckets", "bucket", None, TypeError),
        ("s3_buckets", "bucket", 123, TypeError),
        ("s3_buckets", "bucket", "", ValueError),
        ("s3_buckets", "bucket", "   ", ValueError),
    ],
)
def test_constructor_rejects_invalid_resource_keys(
    resources, constructor_name, resource_name, invalid_key, error
):
    with pytest.raises(error):
        LambdaApiConfig(**{constructor_name: {invalid_key: resources[resource_name]}})


@pytest.mark.parametrize(
    ("method", "invalid_resource"),
    [
        ("add_dynamodb_table", None),
        ("add_dynamodb_table", "orders"),
        ("add_dynamodb_table", 123),
        ("add_s3_bucket", None),
        ("add_s3_bucket", "documents"),
        ("add_s3_bucket", 123),
    ],
)
def test_resource_registry_mutators_reject_obviously_invalid_resources(
    method, invalid_resource
):
    with pytest.raises(TypeError):
        getattr(LambdaApiConfig(), method)("primary", invalid_resource)


@pytest.mark.parametrize(
    ("constructor_name", "invalid_resource"),
    [
        ("dynamodb_tables", None),
        ("dynamodb_tables", "orders"),
        ("dynamodb_tables", 123),
        ("s3_buckets", None),
        ("s3_buckets", "documents"),
        ("s3_buckets", 123),
    ],
)
def test_constructor_rejects_obviously_invalid_resources(
    constructor_name, invalid_resource
):
    with pytest.raises(TypeError):
        LambdaApiConfig(**{constructor_name: {"primary": invalid_resource}})


@pytest.mark.parametrize(
    ("method", "first_name", "second_name", "registry_name"),
    [
        ("add_dynamodb_table", "table", "other_table", "dynamodb_tables"),
        ("add_s3_bucket", "bucket", "other_bucket", "s3_buckets"),
    ],
)
def test_mutator_duplicate_is_rejected_and_original_resource_remains_authoritative(
    resources, method, first_name, second_name, registry_name
):
    config = LambdaApiConfig()
    getattr(config, method)("primary", resources[first_name])

    with pytest.raises(ValueError):
        getattr(config, method)("primary", resources[second_name])

    assert (
        getattr(config._create_resource_builder(), registry_name)["primary"]
        is resources[first_name]
    )


@pytest.mark.parametrize(
    ("constructor_name", "method", "first_name", "second_name", "registry_name"),
    [
        (
            "dynamodb_tables",
            "add_dynamodb_table",
            "table",
            "other_table",
            "dynamodb_tables",
        ),
        ("s3_buckets", "add_s3_bucket", "bucket", "other_bucket", "s3_buckets"),
    ],
)
def test_constructor_registration_is_duplicate_for_later_mutator(
    resources, constructor_name, method, first_name, second_name, registry_name
):
    config = LambdaApiConfig(
        **{constructor_name: {"primary": resources[first_name]}}
    )

    with pytest.raises(ValueError):
        getattr(config, method)("primary", resources[second_name])

    assert (
        getattr(config._create_resource_builder(), registry_name)["primary"]
        is resources[first_name]
    )


def test_constructor_shallow_copies_registry_inputs_without_rewriting_keys(resources):
    tables = {" orders ": resources["table"]}
    buckets = {" documents ": resources["bucket"]}
    config = LambdaApiConfig(dynamodb_tables=tables, s3_buckets=buckets)

    tables["later"] = resources["other_table"]
    buckets.clear()
    builder = config._create_resource_builder()

    assert builder.dynamodb_tables == {" orders ": resources["table"]}
    assert builder.s3_buckets == {" documents ": resources["bucket"]}
    assert builder.dynamodb_tables[" orders "] is resources["table"]
    assert builder.s3_buckets[" documents "] is resources["bucket"]


def test_config_mutation_only_affects_later_resource_registry_snapshot(resources):
    config = LambdaApiConfig(
        dynamodb_tables={"orders": resources["table"]},
        s3_buckets={"documents": resources["bucket"]},
    )
    first = config._create_resource_builder()

    config.add_dynamodb_table("customers", resources["other_table"])
    config.add_s3_bucket("archive", resources["other_bucket"])
    second = config._create_resource_builder()

    assert set(first.dynamodb_tables) == {"orders"}
    assert set(first.s3_buckets) == {"documents"}
    assert set(second.dynamodb_tables) == {"orders", "customers"}
    assert set(second.s3_buckets) == {"documents", "archive"}


def test_builder_registry_mutation_does_not_mutate_config_or_other_builder(resources):
    config = LambdaApiConfig(
        dynamodb_tables={"orders": resources["table"]},
        s3_buckets={"documents": resources["bucket"]},
    )
    first = config._create_resource_builder()
    second = config._create_resource_builder()

    # Direct inspection is intentional until permission resolution supplies a public
    # observable boundary for these lower-level ResourceBuilder registries.
    assert first.dynamodb_tables is not second.dynamodb_tables
    assert first.s3_buckets is not second.s3_buckets
    assert first.dynamodb_tables["orders"] is second.dynamodb_tables["orders"]
    assert first.s3_buckets["documents"] is second.s3_buckets["documents"]
    first.dynamodb_tables["builder-only"] = resources["other_table"]
    first.s3_buckets.clear()

    third = config._create_resource_builder()
    assert set(second.dynamodb_tables) == {"orders"}
    assert set(second.s3_buckets) == {"documents"}
    assert set(third.dynamodb_tables) == {"orders"}
    assert set(third.s3_buckets) == {"documents"}


def test_resource_builder_constructor_stores_separate_registry_mappings(resources):
    tables = {"shared": resources["table"]}
    buckets = {"shared": resources["bucket"]}

    builder = ResourceBuilder(dynamodb_tables=tables, s3_buckets=buckets)

    assert builder.dynamodb_tables is tables
    assert builder.s3_buckets is buckets
    assert builder.dynamodb_tables["shared"] is resources["table"]
    assert builder.s3_buckets["shared"] is resources["bucket"]


def test_legacy_custom_registries_retain_replacement_semantics():
    config = LambdaApiConfig()
    first, second = object(), object()

    config.add_custom_role("shared", first)
    config.add_custom_role("shared", second)

    assert config._create_resource_builder().custom_roles["shared"] is second
