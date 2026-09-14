# Lambda API Decorators CDK

## A library for AWS API Gateway/Lambda Proxy Integration

Lambda API Decorators CDK allows simplified resource creation for AWS Lambda functions and Rest API resources by using decorators and setting a builder with default, common or custom values for IAM Roles, Runtimes, Timeouts, Layers, Environment values, etc. This project relies abstract syntactic trees (ast) to analyze the code of your lambda functions and generate infraestructure accordingly.

### Installation

`lambda_api_decorators_cdk` is available from PyPI as `lambda-api-decorators-cdk`:

    pip install lambda-api-decorators-cdk

Installation of [lambda-api-decorators](https://pypi.org/project/lambda-api-decorators/) is also required as a dependency for your lambda functions, since it provides the definition of decorators used within this module.


### Example

```python
    import lambda_api_decorators_cdk
    or
    from lambda_api_decorators_cdk import ResourceBuilder
```

### Builder instance

You may define a builder using lambda_api_decorators_cdk's constructor `ResourceBuilder`. This method returns an instance of the class that will be used to configure and create your Lambda Functions. By default, no parameters are required to instantiate the object, but custom options may be passed in advanced use cases.

```python
    from lambda_api_decorators_cdk import ResourceBuilder

    builder = ResourceBuilder()
```

### Builder Configuration

If opted to, you can set default values for IAM Roles, Memory Size, Timeout, Runtime and VPC.

On the same note, support for common configuration that all the Lambda Functions will receive, such as Security Groups, Environment variables and Layers, is provided.

Lastly you can setup custom environments, layers, security groups, vpcs a Lambda Function will receive ONLY if they have the decorators defined.

```python
    from lambda_api_decorators_cdk import ResourceBuilder
    from aws_cdk import Duration

    builder = ResourceBuilder()
    builder.set_default_timeout(Duration.seconds(30))
    builder.add_common_environment("DATABASE_URI", "something-db-related")
    builder.add_custom_environment("URL-PREFIX", "lambda-api-decorators-cdk-") #Lambda Function should have decorator @environment("URL-PREFIX")
```

### Building

Assuming you have already instantiated a Builder, configured it and ready to deploy your stack, then simply define the directory of your Lambda Functions and build!

Note: For a Lambda Function to be recognised and built, it has to have a decorator specifying the HTTP method it responds to. Decorators are defined in the [lambda-api-decorators](https://pypi.org/project/lambda-api-decorators/) package.

```python
[...] # Imports

class LambdaApiDecoratorsExampleStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        [...]  # Instantiating builder, defining options and layers...

        lambda_path = 'lambdas'

        restapi = apigateway.RestApi(
            self, 'lambda-api-decorators-RestApi',
            rest_api_name= 'lambda-api-decorators-restApi')
        root_resource = restapi.root

        builder.build(self, root_resource, lambda_path, print_tree=True)

```

## Maintainer releases

The Git tag is the single source of truth for this package's version. For
example, `v0.3.0` produces Python package version `0.3.0`. This repository is
versioned independently from `lambda-api-decorators`.

To release from `main`, choose and push a semantic version tag:

```bash
git checkout main
git pull

git tag v0.3.0
git push origin v0.3.0
```

Pushing the tag triggers the release workflow, which tests, builds, verifies
the version, and publishes with PyPI trusted publishing. The PyPI project must
have a trusted publisher configured for this repository, the `release.yml`
workflow, and the `pypi` GitHub environment.
