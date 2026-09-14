import ast

import pytest

from conftest import decorator_invocations
from lambda_api_decorators_cdk.ast_helper import get_file_nodes


def parse_methods(source):
    resources = get_file_nodes(ast.parse(source), "handler.py", "lambdas")
    return [method for resource in resources for method in resource.get_methods()]


def parse_method(source):
    return parse_methods(source)[0]


def test_authorizer_invocation_is_captured_losslessly():
    method = parse_method(
        '@GET("/admin")\n@authorizer(" users ")\ndef handler(event, context): pass\n'
    )
    assert decorator_invocations(method) == [
        ("GET", ("/admin",), ()),
        ("authorizer", (" users ",), ()),
    ]


@pytest.mark.parametrize(
    "decorator",
    [
        "authorizer()",
        'authorizer("users", "extra")',
        'authorizer(key="users")',
        "authorizer(123)",
        'authorizer("")',
        'authorizer("   ")',
        "authorizer(AUTHORIZER_KEY)",
        "authorizer(get_key())",
        'authorizer(f"{tenant}-users")',
    ],
)
def test_invalid_authorizer_syntax_fails_during_source_interpretation(decorator):
    with pytest.raises((TypeError, ValueError), match="(?i)authorizer"):
        parse_method(
            f'@GET("/admin")\n@{decorator}\ndef handler(event, context): pass\n'
        )


def test_bare_public_is_captured_and_called_public_is_rejected():
    method = parse_method(
        '@GET("/health")\n@public\ndef handler(event, context): pass\n'
    )
    assert decorator_invocations(method) == [
        ("GET", ("/health",), ()),
        ("public", (), ()),
    ]
    with pytest.raises((TypeError, ValueError), match="(?i)public"):
        parse_method(
            '@GET("/health")\n@public()\ndef handler(event, context): pass\n'
        )


@pytest.mark.parametrize(
    "decorators,expected",
    [
        (
            '@GET("/admin")\n@authorizer("admins")',
            [("GET", ("/admin",), ()), ("authorizer", ("admins",), ())],
        ),
        (
            '@authorizer("admins")\n@GET("/admin")',
            [("authorizer", ("admins",), ()), ("GET", ("/admin",), ())],
        ),
        (
            '@GET("/health")\n@public',
            [("GET", ("/health",), ()), ("public", (), ())],
        ),
        (
            '@public\n@GET("/health")',
            [("public", (), ()), ("GET", ("/health",), ())],
        ),
    ],
)
def test_auth_metadata_preserves_top_to_bottom_lexical_order(decorators, expected):
    method = parse_method(f"{decorators}\ndef handler(event, context): pass\n")
    assert decorator_invocations(method) == expected


@pytest.mark.parametrize(
    "decorators",
    [
        '@public\n@authorizer("users")',
        '@authorizer("users")\n@public',
        "@public\n@public",
        '@authorizer("users")\n@authorizer("users")',
        '@authorizer("users")\n@authorizer("admins")',
    ],
)
def test_aggregate_auth_conflicts_are_rejected(decorators):
    with pytest.raises(ValueError, match="(?i)(auth|public|conflict|repeat)"):
        parse_method(
            f'@GET("/")\n{decorators}\ndef handler(event, context): pass\n'
        )


@pytest.mark.parametrize("auth", ['@authorizer("users")', "@public"])
def test_auth_on_multi_route_handler_is_rejected_as_ambiguous(auth):
    with pytest.raises(ValueError, match="(?i)(ambiguous|multiple|route|auth)"):
        parse_methods(
            f'@GET("/a")\n@POST("/b")\n{auth}\n'
            "def handler(event, context): pass\n"
        )


def test_multi_route_handler_without_auth_remains_supported():
    methods = parse_methods(
        '@GET("/a")\n@POST("/b")\ndef handler(event, context): pass\n'
    )
    assert [(method.get_method(), method.get_path_to_file()) for method in methods] == [
        ("GET", "lambdas"),
        ("POST", "lambdas"),
    ]
