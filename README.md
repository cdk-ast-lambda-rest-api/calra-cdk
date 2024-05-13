# CDK Ast Lambda Rest API - CDK Packge (CALRA)

## A library for AWS API Gateway/Lambda Proxy Integration

CALRA allows simplified resource creation for AWS Lambda functions and Rest API resources by using decorators and setting a builder with default, common or custom values for IAM Roles, Runtimes, Timeouts, Layers, Environment values, etc. This project relies abstract syntactic trees (ast) to analyze the code of your lambda functions and generate infraestructure accordingly.

### Installation

`calra_cdk` is available from PyPI as `calra-cdk`:

    pip install calra-cdk

Installation of [calra-lambda](https://example.com) is also required as a dependency for your lambda functions, since it provides the definition of decorators used within this module.
You can as well rely on the [calra-example](https://https://github.com/cdk-ast-lambda-rest-api/calra-example) repository to get started.

### Example

```python
    import calra_cdk
    or
    from calra_cdk import ResourceBuilder
```

### Builder instance

You may define a builder using calra_cdk's constructor `ResourceBuilder`. This method returns an instance of the class that will be used to configure and create your Lambda Functions. By default, no parameters are required to instantiate the object, but custom options may be passed in advanced use cases.

```python
    from calra_cdk import ResourceBuilder

    builder = ResourceBuilder()
```

### Builder Configuration

If opted to, you can set default values for IAM Roles, Memory Size, Timeout, Runtime and VPC.

On the same note, support for common configuration that all the Lambda Functions will receive, such as Security Groups, Environment variables and Layers, is provided.

Lastly you can setup custom environments, layers, security groups, vpcs a Lambda Function will receive ONLY if they have the decorators defined.

```python
    from calra_cdk import ResourceBuilder
    from aws_cdk import Duration

    builder = ResourceBuilder()
    builder.set_default_timeout(Duration.seconds(120))
    builder.add_common_environment("DATABASE_URI", "something-db-related")
    builder.add_custom_environment("URL-PREFIX", "calra-cdk-") #Lambda Function should have decorator @environment("URL-PREFIX")
```

### Building

Assuming you have already instantiated a Builder, configured it and ready to deploy your stack, then simply define the directory of your Lambda Functions and build!

Note: For a Lambda Function to be recognised and built, it has to have a decorator specifying the HTTP method it responds to. Again, the [calra-example](https://https://github.com/cdk-ast-lambda-rest-api/calra-example) repository will provide a firm example of a builder setting and lambda proper annotation with decorators using the [calra-lambda](https://example.com) module.

```python
[...] # Imports

class CalraExampleStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        [...]  # Instantiating builder, defining options and layers...

        lambda_path = 'lambdas'

        restapi = apigateway.RestApi(
            self, 'calra-RestApi',
            rest_api_name= 'calra-restApi')
        root_resource = restapi.root

        builder.build(self, root_resource, lambda_path, print_tree=True)

```
