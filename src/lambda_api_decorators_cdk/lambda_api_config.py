from typing import Mapping, Optional, Sequence

from aws_cdk import Duration
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_

from .resource_builder import ResourceBuilder


class LambdaApiConfig:
    """Reusable defaults and named resources for a :class:`LambdaApi` build."""

    def __init__(
        self,
        *,
        runtime: Optional[lambda_.Runtime] = None,
        timeout: Optional[Duration] = None,
        memory_size: Optional[int] = None,
        vpc: Optional[ec2.IVpc] = None,
        vpc_subnets: Optional[ec2.SubnetSelection] = None,
        role: Optional[iam.IRole] = None,
        layers: Optional[Sequence[lambda_.ILayerVersion]] = None,
        security_groups: Optional[Sequence[ec2.ISecurityGroup]] = None,
        environment: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._default_runtime = runtime
        self._default_timeout = timeout
        self._default_memory_size = memory_size
        self._default_vpc = (vpc, vpc_subnets) if vpc is not None else None
        self._default_role = role

        self._common_layers = list(layers) if layers is not None else []
        self._common_security_groups = (
            list(security_groups) if security_groups is not None else []
        )
        self._common_environments = dict(environment) if environment is not None else {}

        self._custom_runtimes = {}
        self._custom_roles = {}
        self._custom_layers = {}
        self._custom_environments = {}
        self._custom_security_groups = {}
        self._custom_vpcs = {}

    def set_default_runtime(self, runtime: Optional[lambda_.Runtime]) -> None:
        self._default_runtime = runtime

    def set_default_timeout(self, timeout: Optional[Duration]) -> None:
        self._default_timeout = timeout

    def set_default_memory_size(self, memory_size: Optional[int]) -> None:
        self._default_memory_size = memory_size

    def set_default_vpc(
        self,
        vpc: Optional[ec2.IVpc],
        vpc_subnets: Optional[ec2.SubnetSelection] = None,
    ) -> None:
        self._default_vpc = (vpc, vpc_subnets) if vpc is not None else None

    def set_default_role(self, role: Optional[iam.IRole]) -> None:
        self._default_role = role

    def add_common_layer(self, layer: lambda_.ILayerVersion) -> None:
        if layer not in self._common_layers:
            self._common_layers.append(layer)

    def add_common_security_group(
        self, security_group: ec2.ISecurityGroup
    ) -> None:
        if security_group not in self._common_security_groups:
            self._common_security_groups.append(security_group)

    def add_common_environment(self, key: str, value: str) -> None:
        self._common_environments[key] = value

    def add_custom_runtime(self, key: str, runtime: lambda_.Runtime) -> None:
        self._custom_runtimes[key] = runtime

    def add_custom_role(self, key: str, role: iam.IRole) -> None:
        self._custom_roles[key] = role

    def add_custom_layer(self, key: str, layer: lambda_.ILayerVersion) -> None:
        self._custom_layers[key] = layer

    def add_custom_environment(self, key: str, value: str) -> None:
        self._custom_environments[key] = value

    def add_custom_security_group(
        self, key: str, security_group: ec2.ISecurityGroup
    ) -> None:
        self._custom_security_groups[key] = security_group

    def add_custom_vpc(
        self,
        key: str,
        vpc: ec2.IVpc,
        vpc_subnets: Optional[ec2.SubnetSelection] = None,
    ) -> None:
        self._custom_vpcs[key] = (vpc, vpc_subnets)

    def _create_resource_builder(self) -> ResourceBuilder:
        """Create an isolated builder snapshot without copying CDK resources."""
        return ResourceBuilder(
            default_runtime=self._default_runtime,
            default_timeout=self._default_timeout,
            default_memory_size=self._default_memory_size,
            default_vpc=self._default_vpc,
            default_role=self._default_role,
            common_layers=list(self._common_layers),
            common_security_groups=list(self._common_security_groups),
            common_environments=dict(self._common_environments),
            custom_runtimes=dict(self._custom_runtimes),
            custom_roles=dict(self._custom_roles),
            custom_layers=dict(self._custom_layers),
            custom_environments=dict(self._custom_environments),
            custom_security_groups=dict(self._custom_security_groups),
            custom_vpcs=dict(self._custom_vpcs),
        )
