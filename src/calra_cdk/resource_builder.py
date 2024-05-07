from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam, 
    Duration, 
    aws_apigateway as apigateway, 
    aws_lambda as lambda_, 
    aws_lambda_python_alpha as _lambda_python)
import os
from calra_cdk import ast_helper

class class_name():

    def __init__(self):
        self.default_runtime = None
        self.default_timeout = None
        self.default_memory_size = None
        self.default_vpc = None
        self.default_role = None
        
        self.common_layers = []
        self.common_security_groups = []
        self.common_environments = {}
        
        self.custom_runtimes = {}
        self.custom_roles = {}
        self.custom_layers = {}
        self.custom_environments = {}
        self.custom_security_groups = {}
        self.custom_vpcs = {}

        self.custom_runtimes.update({'python3.8':lambda_.Runtime.PYTHON_3_8})
        self.custom_runtimes.update({'python3.9':lambda_.Runtime.PYTHON_3_9})
        self.custom_runtimes.update({'python3.10':lambda_.Runtime.PYTHON_3_10})
        self.custom_runtimes.update({'python3.11':lambda_.Runtime.PYTHON_3_11})
        self.custom_runtimes.update({'python3.12':lambda_.Runtime.PYTHON_3_12})

    #Setters
    def set_default_runtime(self, runtime: lambda_.Runtime):
        self.default_runtime = runtime
    
    def set_default_timeout(self, timeout: Duration):
        self.default_timeout = timeout

    def set_default_memory_size(self, memory_size: int):
        self.default_memory_size = memory_size 

    def set_default_vpc(self, vpc, vpc_subnets: list):
        self.default_vpc = (vpc, vpc_subnets)

    def set_default_role(self, role: iam.Role):
        self.default_role = role

    #Adders
    #Esto funciona arriba de lambda o lambda alpha? El 1ro es LayerVersion el 2do PythonLayerVersion
    def add_common_layer(self, layer = lambda_.LayerVersion | _lambda_python.PythonLayerVersion):
        self.common_layers.append(layer) if layer not in self.common_layers else None

    def add_common_security_group(self, security_group):
        self.common_security_groups.append(security_group) if security_group not in self.common_security_groups else None

    def add_common_environment(self, key:str, value):
        self.common_environments.update({key:value})

    def add_custom_vpc(self, name: str, vpc: ec2.Vpc, vpc_subnets: list):
        self.custom_vpcs.update({name:(vpc, vpc_subnets)})
    
    def add_custom_environment(self, name: str, value: str | int | float):
        self.custom_environments.update({name:value})

    def add_custom_runtime(self, name: str, value: lambda_.Runtime):
        self.custom_runtimes.update({name:value})

    def add_custom_role(self, name: str, value: iam.Role):
        self.custom_roles.update({name:value})

    def add_custom_layer(self, name: str, value: lambda_.LayerVersion | _lambda_python.PythonLayerVersion):
        self.custom_layers.update({name:value})

    def add_custom_security_group(self, name: str, value: ec2.SecurityGroup):
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
    
    def get_common_security_groups(self):
        return self.common_security_groups
    
    def get_common_security_group(self, value: str):
        return self.common_security_groups[value]        

    def get_common_environments(self):
        return self.common_environments
    
    def get_common_environment(self, value: str):
        return self.common_environments[value]
    
    def get_custom_layer(self, value: str) -> lambda_.LayerVersion | _lambda_python.PythonLayerVersion:
        if self.custom_layers.get(value):
            return self.custom_layer[value]
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

    def create_lbd_rest_stack(self, construct, api_resource: apigateway.IResource, lambda_path:str, print_tree: bool = False):
        graph = ast_helper.get_lambda_graph(lambda_path)
        if print_tree:
            ast_helper.dump_tree(graph)
        self.build(construct, graph, api_resource)

    def get_options(self, decorators:dict) -> dict:
        options = {}
        options.update({'runtime':self.get_default_runtime()})
        options.update({'memory_size': self.get_default_memory_size()})
        options.update({'timeout': self.get_default_timeout()})
        options.update({'role': self.get_default_role()})
        options.update({'vpc':self.get_default_vpc()})
        options.update({'environment':self.get_common_environments()})
        options.update({'layers':self.get_common_layers()})
        options.update({'security_groups':self.get_common_security_groups()})
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
                options[key].append(self.get_custom_layer(value))
            elif key == 'role':
                options[key].append(self.get_custom_role(value))
            elif key == 'security_group':
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
            layers = options['layers'],
            memory_size=options['memory_size'],
            security_groups= options['security_groups'],
            vpc= None, #options['vpc'][1], #VPC
            vpc_subnets= None, #options['vpc'][2], #VPC Subnets, no deberia andar ya que es una lista de subredes y el parametro acepta mapa
            environment= options['environment'],
            role= options['role'] 
        )
        return lambda_function

    def build(self, construct, graph: ast_helper.Resource, api_resource: apigateway.IResource):

        path = graph.get_path()
        level = path.count('/')
        if level <= 1 and len(path) <= 1: #root '/'
            print("Root Resource for " + path + " doesn't have to be created")
            new_resource = api_resource
            for method in graph.get_methods():
                lbda = self.build_lambda_function(construct, method)
                new_resource.add_method(method.get_method(), apigateway.LambdaIntegration(lbda))
        else:
            resource_name = path[path.rindex('/')+1:]  #path[path.rindex('/')+1 para que sea sin /
            print("Creating resource for " + path + ' as ' + resource_name)
            new_resource = api_resource.add_resource(resource_name)
            for method in graph.get_methods():
                lbda = self.build_lambda_function(construct, method)
                new_resource.add_method(method.get_method(), apigateway.LambdaIntegration(lbda))

        for node in graph.get_connections():
            self.build(construct, node, new_resource)