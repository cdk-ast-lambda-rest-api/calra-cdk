from pathlib import Path

import pytest
from aws_cdk import aws_lambda as lambda_

from lambda_api_decorators_cdk import ResourceBuilder


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _project_metadata():
    try:
        import tomllib
    except ImportError:  # pragma: no cover - exercised by the Python 3.10 CI job
        import tomli as tomllib

    with (PROJECT_ROOT / "pyproject.toml").open("rb") as pyproject:
        return tomllib.load(pyproject)["project"]


def test_package_requires_python_3_10_or_newer():
    assert _project_metadata()["requires-python"] == ">=3.10"


def test_python_3_9_is_not_advertised():
    assert "Programming Language :: Python :: 3.9" not in _project_metadata()["classifiers"]


def test_supported_python_classifiers_cover_3_10_through_3_14():
    classifiers = set(_project_metadata()["classifiers"])
    assert {
        f"Programming Language :: Python :: 3.{minor}"
        for minor in range(10, 15)
    } <= classifiers


def test_builtin_runtime_registry_contains_supported_python_aliases():
    builder = ResourceBuilder()
    assert {
        f"python3.{minor}" for minor in range(10, 15)
    } <= set(builder.custom_runtimes)


@pytest.mark.parametrize(
    ("alias", "expected"),
    [
        ("python3.13", lambda_.Runtime.PYTHON_3_13),
        ("python3.14", lambda_.Runtime.PYTHON_3_14),
    ],
)
def test_new_builtin_runtime_alias_resolves_to_cdk_runtime(alias, expected):
    resolved = ResourceBuilder().get_custom_runtime(alias)
    assert resolved.name == expected.name
    assert resolved.family == expected.family


def test_builtin_runtime_alias_takes_precedence_over_same_named_custom_runtime():
    custom_runtime = object()
    builder = ResourceBuilder(custom_runtimes={"python3.12": custom_runtime})

    resolved = builder.get_custom_runtime("python3.12")
    assert resolved is not custom_runtime
    assert resolved.name == lambda_.Runtime.PYTHON_3_12.name
    assert resolved.family == lambda_.Runtime.PYTHON_3_12.family
