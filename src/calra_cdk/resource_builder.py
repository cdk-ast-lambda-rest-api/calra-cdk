from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam, 
    Duration, 
    aws_apigateway as apigateway, 
    aws_lambda as lambda_, 
    aws_lambda_python_alpha as _lambda_python)
import os
from calra_cdk import ast_helper
from typing import Optional, List, Dict

class ResourceBuilder():
    '''
    Entrypoint to calra_cdk's functionality. Create a Builder object and set the custom requirements for your Lambda Functions.

    Refer to the constructor method to get started instantiating a builder. 

    For more configuration options, use the set_default_XXXX, add_common_XXXX and add_custom_XXXX methods to add VPCs, Layers, Roles, Runtimes, Security Groups and Environment Variables. 
    '''

    def __init__(self,
                default_runtime: Optional[lambda_.Runtime] = None,
                default_timeout: Optional[Duration] = None,
                default_memory_size: Optional[int] = None,
                default_vpc = None,
                default_role: Optional[iam.Role] = None,
                common_layers: List = [],
                common_security_groups: List[ec2.SecurityGroup] = [],
                common_environments: Dict[str, str] = {},
                custom_runtimes: Dict[str, lambda_.Runtime] = {},
                custom_roles: Dict[str, iam.Role] = {},
                custom_layers: Dict[str, None] = {}, ####TODO
                custom_environments: Dict[str, str] = {},
                custom_security_groups: Dict[str, ec2.SecurityGroup] = {},
                custom_vpcs = {} ####TODO
                ) -> 'ResourceBuilder':
    
        '''
        Creates base instance of a Resource Builder. By default, there are no predetermined custom, common nor default settings with the exception of the following custom runtimes: python3.8, python3.9, python.10, python.11, python.12.
        You can optionally specify arguments (Keep in mind some of them are constructs of the aws_cdk toolkit) such as:
        @param default_runtime
        @param default_timeout
        @param default_memory_size
        @param default_vpc
        @param default_role
        @param common_layers
        @param common_security_groups
        @param common_environments
        @param custom_runtimes
        @param custom_roles
        @param custom_layers
        @param custom_environments
        @param custom_security_groups
        @param custom_vpcs
        '''
        # Check and set properties based on provided keyword arguments
        self.default_runtime = default_runtime
        self.default_timeout = default_timeout
        self.default_memory_size = default_memory_size
        self.default_vpc = default_vpc
        self.default_role = default_role
        
        self.common_layers = common_layers
        self.common_security_groups = common_security_groups
        self.common_environments = common_environments
        
        self.custom_runtimes = custom_runtimes
        self.custom_roles = custom_roles
        self.custom_layers = custom_layers
        self.custom_environments = custom_environments
        self.custom_security_groups = custom_security_groups
        self.custom_vpcs = custom_vpcs

        self.custom_runtimes.update({'python3.8':lambda_.Runtime.PYTHON_3_8})
        self.custom_runtimes.update({'python3.9':lambda_.Runtime.PYTHON_3_9})
        self.custom_runtimes.update({'python3.10':lambda_.Runtime.PYTHON_3_10})
        self.custom_runtimes.update({'python3.11':lambda_.Runtime.PYTHON_3_11})
        self.custom_runtimes.update({'python3.12':lambda_.Runtime.PYTHON_3_12})


    #Setters
    def set_default_runtime(self, runtime: lambda_.Runtime):
        '''Set the default runtime every Lambda Function in the scope of the builder will have.'''
        self.default_runtime = runtime
    
    def set_default_timeout(self, timeout: Duration):
        '''Set the default timeout every Lambda Function in the scope of the builder will have. If not specified, timeout will be CDK's default.'''
        self.default_timeout = timeout

    def set_default_memory_size(self, memory_size: int):
        '''Set the default memory size every Lambda Function in the scope of the builder will have. If not specified, memory size will be CDK's default.'''
        self.default_memory_size = memory_size 

    def set_default_vpc(self, vpc, vpc_subnets: list):
        '''Set the default VPC and Subnets every Lambda Function in the scope of the builder will have. If not specified, none will be assigned to Lambda.'''
        self.default_vpc = (vpc, vpc_subnets)

    def set_default_role(self, role: iam.Role):
        '''Set the default Role and permissions every Lambda Function in the scope of the builder will have. If not specified, CDK will create it's own for your Lambda.'''
        self.default_role = role

    #Adders
    def add_common_layer(self, layer = lambda_.LayerVersion | _lambda_python.PythonLayerVersion):
        '''Add a common layer for all your Lambda Functions.'''
        self.common_layers.append(layer) if layer not in self.common_layers else None

    def add_common_security_group(self, security_group):
        '''Add a common security group for all your Lambda Functions.'''
        self.common_security_groups.append(security_group) if security_group not in self.common_security_groups else None

    def add_common_environment(self, key:str, value):
        '''Add a common environment variable and value for all your Lambda Functions.'''
        self.common_environments.update({key:value})

    def add_custom_vpc(self, name: str, vpc: ec2.Vpc, vpc_subnets: list):
        self.custom_vpcs.update({name:(vpc, vpc_subnets)})
    
    def add_custom_environment(self, name: str, value: str | int | float):
        '''Add a custom environment variable and value for every lambda function with the decorator @environment(name).'''
        self.custom_environments.update({name:value})

    def add_custom_runtime(self, name: str, value: lambda_.Runtime):
        '''Add a custom Rruntime for every lambda function with the decorator @runtime(name).'''
        self.custom_runtimes.update({name:value})

    def add_custom_role(self, name: str, value: iam.Role):
        '''Add a custom Role for every lambda function with the decorator @role(name).'''
        self.custom_roles.update({name:value})

    def add_custom_layer(self, name: str, value: lambda_.LayerVersion | _lambda_python.PythonLayerVersion):
        '''Add a custom Layer for every lambda function with the decorator @layer(name).'''
        self.custom_layers.update({name:value})

    def add_custom_security_group(self, name: str, value: ec2.SecurityGroup):
        '''Add a custom security group for every lambda function with the decorator @security_group(name).'''
        self.custom_layers.update({name:value})


    #Getters
    def get_default_runtime(self) -> lambda_.Runtime | None:
        return self.default_runtime
    
    def get_default_timeout(self) -> Duration | None:
        return self.default_timeout

    def get_default_memory_size(self) -> int | None:
        return self.default_memory_size

    def get_default_vpc(self) -> tuple | None:
        return self.default_vpc

    def get_default_role(self) -> iam.Role | None:
        return self.default_role
    
    def get_common_layers(self) -> list | None:
        return self.common_layers

    def get_common_layer(self, value: str) -> lambda_.LayerVersion | _lambda_python.PythonLayerVersion:
        return self.common_layers[value]
    
    def get_common_security_groups(self) -> list | None:
        return self.common_security_groups
    
    def get_common_security_group(self, value: str):
        return self.common_security_groups[value]        

    def get_common_environments(self):
        return self.common_environments
    
    def get_common_environment(self, value: str):
        return self.common_environments[value]
    
    def get_custom_layer(self, value: str) -> lambda_.LayerVersion | _lambda_python.PythonLayerVersion:
        if self.custom_layers.get(value):
            return self.custom_layers[value]
        else: raise KeyError(name=f'Value {value} not previously declared as custom layer')

    def get_custom_roles(self):
        return self.custom_roles
    
    def get_custom_role(self, value: str) -> iam.Role:
        if self.custom_roles.get(value):
            return self.custom_roles[value]
        else: raise KeyError(name=f'Value {value} not previously declared as custom role')
    
    def get_custom_security_group(self, value: str) -> ec2.SecurityGroup:
        if self.custom_security_groups.get(value):
            return self.custom_security_groups[value]
        else: raise KeyError(name=f'Value {value} not previously declared as custom security group')
    
    def get_custom_environment(self, value: str) -> str:
        if self.custom_environments.get(value):
            return self.custom_environments[value]
        else: raise KeyError(name=f'Value {value} not previously declared as custom environment')
    
    def get_custom_runtime(self, value: str) -> lambda_.Runtime: 
        if self.custom_runtimes.get(value):
            return self.custom_runtimes[value]
        else: raise KeyError(name=f'Value {value} not previously declared as custom runtime')
    
    def get_custom_vpc(self, value: str) -> tuple:
        #TODO
        return self.custom_vpcs[value]

    def build(self, construct, api_resource: apigateway.IResource, lambda_path:str, print_tree: bool = False):
        '''
        Dynamically create Lambda Functions and Rest Api resources based on the options assigned to the builder.
        @param construct: Stack which new resources and functions will be assigned to.
        @param api_resource: REST API root resource from which the new resources/endpoints will be added.
        @param lambda_path: Relative path (from cdk project workspace root dir) to the lambda functions defined.
        @param print_tree: Optional value to output to terminal the API and functions built in a tree syntaxis.. Defaults to False.
        '''

        graph = ast_helper.get_lambda_graph(lambda_path)
        if print_tree:
            ast_helper.dump_tree(graph)
        self.build_from_graph(construct, graph, api_resource)

    def get_options(self, decorators:dict) -> dict:
        options = {}
        options.update({'runtime':self.get_default_runtime()})
        options.update({'memory_size': self.get_default_memory_size()})
        options.update({'timeout': self.get_default_timeout()})
        options.update({'role': self.get_default_role()})
        options.update({'vpc':self.get_default_vpc()})
        options.update({'environment':dict(self.get_common_environments())})
        options.update({'layer': list(self.get_common_layers())})
        options.update({'security_group':list(self.get_common_security_groups())})
        #Optional values that may be or not be overriden
        options.update({'description':None})
        options.update({'name':None})
        #Add defaults and let the decorators overwrite them (in case of defaults) or aggregate them (in case of common)
        for key, value in decorators.items():
            if key in ['memory_size','description','name']:
                options.update({key: value})
            elif key ==  'runtime':
                options[key] = self.get_custom_runtime(value)
            elif key == 'timeout':
                timeout = Duration.seconds(value)
                options.update({key: timeout})
            elif key == 'layer':
                if type(value) == list:
                    for v in value:
                        options[key].append(self.get_custom_layer(v))
                else:
                    options[key].append(self.get_custom_layer(value))
            elif key == 'role':
                options[key].append(self.get_custom_role(value))
            elif key == 'security_group':
                if type(value) == list:
                    for v in value:
                        options[key].append(self.get_custom_environment(v))
                else:
                    options[key].append(self.get_custom_security_group(value))
            elif key == 'environment':
                if type(value) == list:
                    for v in value:
                        options[key][v] = self.get_custom_environment(v)
                else:
                    options[key][value] = self.get_custom_environment(value)
            elif key == 'vpc':
                options[key] = self.get_custom_vpc(value)
        return options

    def build_lambda_function(self, construct, method: ast_helper.Method):
        # Create Lambda function with aggregated metadata from all decorators

        logical_id = method.get_logical_id()
        handler = method.get_handler()
        file = method.get_file()
        entry_path = method.get_path_to_file()
        options = self.get_options(method.get_decorators())
        lambda_function = _lambda_python.PythonFunction(
            construct, logical_id,
            function_name = options['name'] if options['name'] else logical_id,
            description = options['description'],
            entry = entry_path,
            index = file,
            handler = handler,
            runtime = options['runtime'],
            timeout = options['timeout'],
            layers = options['layer'],
            memory_size=options['memory_size'],
            security_groups= options['security_group'],
            vpc= None, 
            vpc_subnets= None, 
            environment= options['environment'],
            role= options['role'] 
        )
        return lambda_function

    def build_from_graph(self, construct, graph: ast_helper.Resource, api_resource: apigateway.IResource):

        path = graph.get_path()
        level = path.count('/')
        if level <= 1 and len(path) <= 1: #root '/'
            new_resource = api_resource
            for method in graph.get_methods():
                lbda = self.build_lambda_function(construct, method)
                new_resource.add_method(method.get_method(), apigateway.LambdaIntegration(lbda))
        else:
            #We can get a skip from /something to /something/one/two/method, so resources with no methods "one" and "two" should be created
            new_api_resources = path[len(api_resource.path)+1:].split('/')
            if len(new_api_resources) > 1: #Resources with no methods associated need to be created. No possible conflict because graph is sorted.
                for res in new_api_resources[:-1]: # Exclude last resource that will be created w/lambda
                    api_resource = api_resource.add_resource(res)
            resource_name = path[path.rindex('/')+1:] #Now we can create the resource associated with the node even if 
            new_resource = api_resource.add_resource(resource_name)
            for method in graph.get_methods():
                lbda = self.build_lambda_function(construct, method)
                new_resource.add_method(method.get_method(), apigateway.LambdaIntegration(lbda))

        for node in graph.get_connections():
            self.build_from_graph(construct, node, new_resource)