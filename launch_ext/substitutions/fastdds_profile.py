from launch.launch_context import LaunchContext
from launch.substitution import Substitution
from launch.substitutions import (
    PathJoinSubstitution,
    LaunchLogDir
)
from launch_ros.substitutions import FindPackageShare

from .resolve_host import ResolveHost
from .ros_distro import ROSDistro

from .jinja_template import JinjaTemplate

from ..discovery.discovery_config import IPEndPoint



def resolve_endpoint(endpoint: IPEndPoint, context: LaunchContext) -> IPEndPoint:
    resolved_address = ResolveHost(endpoint.address).perform(context)
    return IPEndPoint(address=resolved_address, port=endpoint.port)


class FastDDSProfile(Substitution):
    """Substitution that renders a FastDDS profile XML from a Jinja2 template."""

    def __init__(
        self,
        discovery_protocol: str = "CLIENT",
        local_discovery_server: IPEndPoint | None = None,
        external_interfaces: list[str] | None = None,
        external_discovery_servers: list[IPEndPoint] | None = None,
        shm_large_segment: bool = False,
        domain_id: int | None = None,
    ):
        self.discovery_protocol = discovery_protocol
        self.local_discovery_server = local_discovery_server
        self.external_interfaces = [ResolveHost(iface) for iface in external_interfaces] if external_interfaces else []
        self.external_discovery_servers = external_discovery_servers
        self.shm_large_segment = shm_large_segment
        self.domain_id = domain_id

        self.template_vars = {
                "discovery_protocol": self.discovery_protocol,
                "local_discovery_server": self.local_discovery_server,
                "external_interfaces": self.external_interfaces,
                "external_discovery_servers": self.external_discovery_servers,
                "shm_large_segment": self.shm_large_segment,
                "domain_id": self.domain_id,
                "ros_distro": ROSDistro(),
                "launch_log_dir": LaunchLogDir(),
        }

        self.jtemplate = JinjaTemplate(
            template_path=PathJoinSubstitution([FindPackageShare("launch_ext"), "config", "fastdds_profile.xml.j2"]),
            template_vars=self.template_vars
        )

    def perform(self, context: LaunchContext) -> str:
        # I guess there's no way to really resolve this with the launch system
        self.template_vars["external_discovery_servers"] = [resolve_endpoint(srv, context) for srv in self.template_vars["external_discovery_servers"]] if self.template_vars["external_discovery_servers"] else []
        self.template_vars["local_discovery_server"] = resolve_endpoint(self.template_vars["local_discovery_server"], context) if self.template_vars["local_discovery_server"] else None
        return self.jtemplate.perform(context)

    def describe(self):
        return f"FastDDSProfile({self.template_vars})"
