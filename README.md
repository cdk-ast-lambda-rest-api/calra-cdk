# CDK Ast Lambda Rest API - CDK Packge (CALRA)

# A library for AWS API Gateway/Lambda Proxy Integration

CALRA allows simplified resource creation for AWS Lambda functions and Rest API resources by using decorators and setting a builder with default, common or custom values for IAM Roles, Runtimes, Timeouts, Layers, Environment values, etc. This project relies abstract syntactic trees (ast) to analyze the code of your lambda functions and generate infraestructure accordingly.

## Installation

`calra_cdk` is available from PyPI as `calra-cdk`::

    pip install calra-cdk

We also encourage the installation of `calra-lambda <https://example.com>` as a dependency for your lambda functions, since it will provide the definition of decorators.
You can as well rely on the `calra-example <https://https://github.com/cdk-ast-lambda-rest-api/calra-example>` repository to get started.

## Example

```python

    import calra-cdk

```
