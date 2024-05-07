import ast
import os

class Method:
    ALLOWED_METHODS = {'PUT', 'POST', 'GET', 'DELETE', 'ANY'}

    def __init__(self, path_to_file:str, file: str, handler: str, method: str, decorators: dict):
        '''One http method is always associated with a file:handler entrypoint in a one-to-one relationship and each handler has decorators in a one-to-many relationship'''
        if method not in self.ALLOWED_METHODS:
            raise ValueError(f'Invalid method: {method}. Allowed methods are {', '.join(self.ALLOWED_METHODS)}')
        self.method = method
        self.file = file.replace(os.sep, '/')
        self.path_to_file = path_to_file.replace(os.sep, '/')
        self.handler = handler
        self.decorators = decorators

    def __str__(self):
        return (self.get_method(), self.get_file(), self.get_handler())

    def get_method(self):
        return self.method
    
    def get_logical_id(self):
        return self.get_file().replace('.','dot').replace('/','-') + '-' + self.get_handler() #No puedo poner el os.sep aca porque como compila en windows no toma el '/'
    
    def get_file(self):
        return self.file

    def get_handler(self):
        return self.handler       

    def get_path_to_file(self):
        return self.path_to_file
    
    def get_method(self):
        return self.method    
    
    def get_decorators(self):
        return self.decorators
    
    # def add_decorators(self, dict):
    #     print(dict)
    #     self.decorators.update(dict)
    
    def __eq__(self, other):
        try:
            check = self.get_method() == other.get_method and self.get_handler() == other.get_handler()
            if check:
                raise ValueError(f'{self.file()} and {other.get_file()} define the same method and handler, implementation may vary')
            return isinstance(other, Method) and check
        except TypeError:
            raise TypeError


class Resource:
    def __init__(self, path = '/'):
        self.path = path
        self.methods = []
        self.connections = []

    def get_path(self) -> str:
        return self.path
    
    def get_methods(self) -> list[Method]:
        return self.methods
    
    def get_connections(self) -> list['Resource']:
        return self.connections

    def __eq__(self, other):
        return isinstance(other, Resource) and self.get_path() == other.get_path()

    def __str__(self):
        methods_str = ' '
        for method in self.get_methods():
            methods_str = '(' + str(method.__str__()) + ') '
            #methods_str = methods_str + '(' + method.get_method() + ' at ' + method.get_logical_id() + ') '
        return self.get_path() + methods_str 
    
    #Validar GET PUT UPDATE DELETE? QUE NO SE REPITA?
    def add_method(self, method: Method) -> bool:
        '''Aggregate Method to present Resource's endpoint'''
        if method not in self.methods:
            self.methods.append(method)
            return True
        else:
            return False
        
    def add_methods(self, method: list[Method]) -> bool:
        '''Aggregate Methods to present Resource's endpoint'''
        for method in self.methods:
            if method not in self.methods:
                self.methods.append(method)
            return True

    def includes_path(self, sub_path) -> bool:
        '''Will indicate if another's Resource path is a ramification of the present Resource'''
        return True if sub_path.startswith(self.path) else False

    def connect(self, resource: 'Resource') -> bool:
        if self.includes_path(resource.get_path()) and resource not in self.get_connections():
            self.connections.append(resource)
            return True
        return False

    def get_matching_prefix_index(self, ext_path: str) -> int:
        current_path = self.get_path()
        matching_prefix_index = ext_path.index(current_path) + len(current_path) if current_path in ext_path else -1
        return matching_prefix_index
        #We should always have a longest prefix match index at 1 because '/'
    
    def clone(self) -> 'Resource':
        clone = Resource(self.get_path())
        clone.connections = self.get_connections()
        clone.methods = self.get_methods()
        return clone

    def insert_node(self, resource: 'Resource') -> bool:
        resource_path = resource.get_path()

        #Edge cases: Resource refers to same endpoint / Resource comes before  / Resource goes deeper or next to current node as bifurcation
        if resource_path == self.get_path(): #They have the same path, new resource comes from a different function/file so we merge
            for method in resource.get_methods():
                self.add_method(method)
            for connection in resource.get_connections():
                self.connect(connection)
            return True

        if len(resource_path) < len(self.get_path()) and self.get_path() in resource_path: #Given resource comes before current, so we have to switch them
            aux = self.clone(self)
            self.methods = resource.get_methods()
            self.connections = resource.get_connections()
            self.path = resource.get_path()
            resource.connect(aux)
            return True
        elif len(resource_path) >= len(self.get_path()) and resource_path.startswith(self.get_path()): #Resource goes deeper or bifurcation
            if len(self.get_connections()) < 1:
                self.connect(resource)
                return True
            else:
                matching_node = self
                matching_prefix_index = self.get_matching_prefix_index(resource_path)
                for node in self.get_connections():
                    if node.get_path() in resource_path:
                        node_matching_index = node.get_matching_prefix_index(resource_path)
                        if node_matching_index > matching_prefix_index:
                            matching_prefix_index = node_matching_index
                            matching_node = node
                if resource_path.startswith(matching_node.get_path()) and matching_node.get_path() not in self.get_path(): #Goes deeper
                    return matching_node.insert_node(resource)
                else: #Bifurcation
                    self.connect(resource)
                    return True
        else: #We should never get to this case because the root path would be '/' so we always have a startswith match.
            self.connect(resource)
            return True

def parse_file(file_path):
    with open(file_path, 'r') as file:
        source_code = file.read()
        return ast.parse(source_code, filename=file_path)


def get_file_nodes(parsed_tree, id, directory):
    node_list = []
    for node in parsed_tree.body:
        if isinstance(node, ast.FunctionDef):
            is_lambda_http = False
            method_decorators = {}
            func_name = node.name
            paths = {} #A handler could have multiple paths with multiple HTTP methods
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    http_decorator = False
                    # Handle decorators with arguments
                    decorator_name = ast.unparse(decorator.func).strip()
                    # An HTTP request will always have an endpoint
                    if decorator_name in {'GET', 'PUT', 'DELETE', 'POST'}:
                        http_decorator = True
                        is_lambda_http = True
                        #First argument should be path
                        path = decorator.args[0].s
                        if http_decorator:
                            paths.update({path:decorator_name})
                    else:
                        if len(decorator.args) > 1:
                            args = [arg.s for arg in decorator.args]
                            method_decorators.setdefault(decorator_name, []).extend(args)
                        else:
                            if isinstance(decorator.args[0], ast.List):
                                value = [elt.s for elt in decorator.args[0].elts]
                                print(value)
                            else:
                                value = decorator.args[0].s
                            method_decorators.setdefault(decorator_name, value) 
                else:
                    # Handle decorators without arguments
                    decorator_name = ast.unparse(decorator).strip()
                    # Aggregate metadata from all decorators
                    method_decorators.setdefault(decorator_name, [])

            #ast.FunctionDef ends. If the Function had an HTTP Decorator it means it's a lambda function
            if is_lambda_http: 
                for key,value in paths.items():
                    #If id (file) is at the root of directory, no change needed. Else we need to only get the file
                    filepath = id[id.rindex(os.sep)+1:] if id.count(os.sep) > 0 else id 
                    #Concatenate directory to id (file) for lambda entry point /  separate "index" file from path
                    full_path = os.path.join(directory,id)
                    
                    method = Method(path_to_file=full_path[:full_path.rindex(os.sep)], file= filepath, handler=func_name, method=value, decorators=method_decorators)
                    node_exists = False
                    if len(node_list) > 0:
                        for node in node_list:
                            if node.get_path() == key:
                                node.add_method(method)
                                node_exists = True
                    if not node_exists:
                        new_resource = Resource(path=key)
                        new_resource.add_method(method)
                        node_list.append(new_resource)

    return node_list

def dump_tree(node, level=0):
    if node is None:
        return

    # Print current node with indentation
    print("   " * level, node)

    # Recursively print connections
    for child in node.get_connections():
        dump_tree(child, level + 1)

def has_decorators(parsed_tree):
    for node in ast.walk(parsed_tree):
        if isinstance(node, ast.FunctionDef) and node.decorator_list: #Es necesario fijarme si tiene si o si un decorador de tipo http? o con que tenga alcanza
            return True
    return False


def get_lambda_graph(directory):
    python_files = []
    graph = Resource('/')
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    
    for file in python_files:
        parsed_tree = parse_file(file)
        file_id = file[len(directory)+len(os.sep):]
        if has_decorators(parsed_tree):
            new_nodes = get_file_nodes(parsed_tree, file_id, directory)
            for node in new_nodes:
                graph.insert_node(node)
        else:
            print("Skipped " + file + ' due to it not having decorators')
    return graph
