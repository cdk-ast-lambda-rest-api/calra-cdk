import ast
import os
from dataclasses import dataclass
from typing import Any, Tuple


@dataclass(frozen=True)
class DecoratorInvocation:
    """A single decorator call captured without interpreting its purpose."""

    name: str
    args: Tuple[Any, ...]
    kwargs: Tuple[Tuple[str, Any], ...]

class Method:
    ALLOWED_METHODS = {'PUT', 'POST', 'GET', 'DELETE', 'ANY'}

    def __init__(self, path_to_file:str, file: str, handler: str, method: str, decorators):
        '''One http method is always associated with a file:handler entrypoint in a one-to-one relationship and each handler has decorators in a one-to-many relationship'''
        if method not in self.ALLOWED_METHODS:
            raise ValueError(f"Invalid method: {method}. Allowed methods are {', '.join(self.ALLOWED_METHODS)}")
        self.method = method
        self.file = file.replace(os.sep, '/')
        self.path_to_file = path_to_file.replace(os.sep, '/')
        self.handler = handler
        if isinstance(decorators, dict):
            decorators = tuple(
                DecoratorInvocation(name, (value,), ())
                for name, value in decorators.items()
            )
        self._decorator_invocations = tuple(decorators)

    def __str__(self):
        return (self.get_method(), self.get_file(), self.get_handler())

    def get_method(self):
        return self.method
    
    def get_logical_id(self):
        return self.get_file().replace('.','dot').replace('/','-') + '-' + self.get_handler()
    
    def get_file(self):
        return self.file

    def get_handler(self):
        return self.handler       

    def get_path_to_file(self):
        return self.path_to_file
    
    def get_method(self):
        return self.method    
    
    def get_decorator_invocations(self):
        return self._decorator_invocations
    
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
        return self.path == '/' or sub_path == self.path or sub_path.startswith(self.path.rstrip('/') + '/')

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
    
    def switch_nodes(self, resource:'Resource'):
        aux = self.clone()
        self.methods = resource.get_methods()
        self.connections = resource.get_connections()
        self.path = resource.get_path()
        resource.connect(aux)
        return True
    
    def insert_node(self, resource: 'Resource') -> bool:
        resource_path = resource.get_path()

        #Edge cases: Resource refers to same endpoint / Resource comes before  / Resource goes deeper or next to current node as bifurcation
        if resource_path == self.get_path(): #They have the same path, new resource comes from a different function/file so we merge
            for method in resource.get_methods():
                self.add_method(method)
            for connection in resource.get_connections():
                self.connect(connection)
            return True
        
        if len(resource_path) < len(self.get_path()) and resource.includes_path(self.get_path()): #Given resource comes before current, so we have to switch them
            # aux = self.clone()
            # self.methods = resource.get_methods()
            # self.connections = resource.get_connections()
            # self.path = resource.get_path()
            # resource.connect(aux)
            # return True
            return self.switch_nodes(resource)
        
        if len(resource_path) >= len(self.get_path()) and self.includes_path(resource_path): #Resource goes deeper or bifurcation
            if len(self.get_connections()) < 1:
                self.connect(resource)
                return True
            else:
                matching_node = self
                matching_prefix_index = self.get_matching_prefix_index(resource_path)
                for node in self.get_connections(): # Check if it goes deeper or may come in between two nodes
                    if node.includes_path(resource_path): #deeper candidate
                        node_matching_index = node.get_matching_prefix_index(resource_path)
                        if node_matching_index > matching_prefix_index:
                            matching_prefix_index = node_matching_index
                            matching_node = node
                    elif resource.includes_path(node.get_path()): #It comes in between, so we have to switch them or guess if it goes deeper
                        return node.insert_node(resource)
                if matching_node.includes_path(resource_path) and matching_node.get_path() != self.get_path(): #Goes deeper/recursion
                    return matching_node.insert_node(resource)
                else: #Bifurcation
                    self.connect(resource)
                    return True
        else: #We should never get to this case because the root path would be '/' so we always have a startswith match in 3rd case for bifurcation
            self.connect(resource)
            return True

def parse_file(file_path):
    with open(file_path, 'r') as file:
        source_code = file.read()
        return ast.parse(source_code, filename=file_path)


def _literal_value(node, decorator_name):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError) as error:
        raise ValueError(
            f"{decorator_name} only supports literal decorator values"
        ) from error


def _require_non_empty_string(value, decorator_name, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{decorator_name} {field} must be a non-empty string")


def _validate_grant(invocation, physical_field):
    name = invocation.name
    kwargs = dict(invocation.kwargs)
    allowed_fields = {"resource_key", physical_field, "access"}
    unexpected = next((key for key in kwargs if key not in allowed_fields), None)
    if unexpected is not None:
        raise ValueError(f"{name} received unexpected field {unexpected}")

    if invocation.args:
        if invocation.kwargs or len(invocation.args) != 2:
            raise ValueError(
                f"{name} positional form requires resource_key and access"
            )
        resource_key, access = invocation.args
        _require_non_empty_string(resource_key, name, "resource_key")
    else:
        has_resource_key = "resource_key" in kwargs
        has_physical_name = physical_field in kwargs
        if has_resource_key == has_physical_name:
            raise ValueError(
                f"{name} requires exactly one of resource_key or {physical_field}"
            )
        address_field = "resource_key" if has_resource_key else physical_field
        _require_non_empty_string(kwargs[address_field], name, address_field)
        if "access" not in kwargs:
            raise ValueError(f"{name} requires access")
        access = kwargs["access"]

    if access not in ("read", "write"):
        raise ValueError(f"{name} access must be read or write, not {access!r}")


def _validate_permission(invocation):
    if invocation.args:
        raise ValueError("permission only accepts keyword arguments")
    kwargs = dict(invocation.kwargs)
    for key in kwargs:
        if key not in ("actions", "resources"):
            raise ValueError(f"permission received unexpected field {key}")
    for field in ("actions", "resources"):
        if field not in kwargs:
            raise ValueError(f"permission requires {field}")
        values = kwargs[field]
        if not isinstance(values, (list, tuple)) or not values:
            raise ValueError(f"permission {field} must be a non-empty sequence")
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError(
                f"permission {field} must contain only non-empty strings"
            )

    normalized = tuple(
        (key, tuple(value) if key in ("actions", "resources") else value)
        for key, value in invocation.kwargs
    )
    return DecoratorInvocation(invocation.name, invocation.args, normalized)


def _parse_invocation(decorator):
    if isinstance(decorator, ast.Name) and decorator.id == "public":
        return DecoratorInvocation(name="public", args=(), kwargs=())
    if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Name):
        return None
    name = decorator.func.id
    if any(keyword.arg is None for keyword in decorator.keywords):
        raise ValueError(f"{name} does not support expanded keyword arguments")
    invocation = DecoratorInvocation(
        name=name,
        args=tuple(_literal_value(arg, name) for arg in decorator.args),
        kwargs=tuple(
            (keyword.arg, _literal_value(keyword.value, name))
            for keyword in decorator.keywords
        ),
    )
    if name == "grant_dynamodb":
        _validate_grant(invocation, "table_name")
    elif name == "grant_s3":
        _validate_grant(invocation, "bucket_name")
    elif name == "permission":
        invocation = _validate_permission(invocation)
    elif name == "authorizer":
        if len(invocation.args) != 1 or invocation.kwargs:
            raise ValueError("authorizer requires exactly one positional key")
        _require_non_empty_string(invocation.args[0], name, "key")
    elif name == "public":
        raise ValueError("public must be used as a bare decorator")
    return invocation


def get_file_nodes(parsed_tree, id, directory):
    node_list = []
    for node in parsed_tree.body:
        if isinstance(node, ast.FunctionDef):
            is_lambda_http = False
            decorator_invocations = []
            func_name = node.name
            paths = [] #A handler could have multiple paths with multiple HTTP methods
            for decorator in node.decorator_list:
                invocation = _parse_invocation(decorator)
                if invocation is None:
                    continue
                decorator_invocations.append(invocation)
                if invocation.name in Method.ALLOWED_METHODS:
                    if len(invocation.args) != 1 or invocation.kwargs:
                        raise ValueError(
                            f"{invocation.name} requires one positional path"
                        )
                    path = invocation.args[0]
                    _require_non_empty_string(path, invocation.name, "path")
                    is_lambda_http = True
                    paths.append((path, invocation.name))

            auth_invocations = [
                invocation for invocation in decorator_invocations
                if invocation.name in ("authorizer", "public")
            ]
            if len(auth_invocations) > 1:
                raise ValueError(
                    "Conflicting or repeated authentication decorators are not allowed"
                )
            if len(paths) > 1 and auth_invocations:
                raise ValueError(
                    "Authentication on a handler with multiple routes is ambiguous"
                )

            #ast.FunctionDef ends. If the Function had an HTTP Decorator it means it's a lambda function
            if is_lambda_http: 
                for key,value in paths:
                    #If id (file) is at the root of directory, no change needed. Else we need to only get the file
                    filepath = id[id.rindex(os.sep)+1:] if id.count(os.sep) > 0 else id 
                    #Concatenate directory to id (file) for lambda entry point /  separate "index" file from path
                    full_path = os.path.join(directory,id)
                    
                    method = Method(path_to_file=full_path[:full_path.rindex(os.sep)], file= filepath, handler=func_name, method=value, decorators=decorator_invocations)
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
