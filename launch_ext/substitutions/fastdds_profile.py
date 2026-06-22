import os

from jinja2 import Environment, FileSystemLoader

from launch.launch_context import LaunchContext
from launch.substitution import Substitution


from launch.substitutions import (
    PathJoinSubstitution,
    LaunchLogDir
)
from launch_ros.substitutions import FindPackageShare
from launch_ext.substitutions import (
    ResolveHost,
)

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
        ros_domain_id: int | None = None,
    ):
        self.discovery_protocol = discovery_protocol
        self.local_discovery_server = local_discovery_server
        self.external_interfaces = external_interfaces
        self.external_discovery_servers = external_discovery_servers
        self.shm_large_segment = shm_large_segment
        self.ros_domain_id = ros_domain_id

    def perform(self, context: LaunchContext) -> str:
        config_dir = PathJoinSubstitution([FindPackageShare("launch_ext"), "config"]).perform(
            context
        )
        env = Environment(
            loader=FileSystemLoader(config_dir),
            keep_trailing_newline=True,
        )
        template = env.get_template("fastdds_profile.xml.j2")

        external_interfaces = [ResolveHost(iface).perform(context) for iface in self.external_interfaces] if self.external_interfaces else []
        external_discovery_servers = [resolve_endpoint(srv, context) for srv in self.external_discovery_servers] if self.external_discovery_servers else []
        if self.local_discovery_server:
            self.local_discovery_server = resolve_endpoint(self.local_discovery_server, context)
        launch_log_dir = LaunchLogDir().perform(context)

        return template.render(
            discovery_protocol=self.discovery_protocol,
            local_discovery_server=self.local_discovery_server,
            launch_log_dir=launch_log_dir,
            external_interfaces=external_interfaces,
            external_discovery_servers=external_discovery_servers,
            shm_large_segment=self.shm_large_segment,
            ros_domain_id=self.ros_domain_id,
            ros_distro=os.environ.get("ROS_DISTRO", "kilted"),
        )

    def describe(self):
        return f"FastDDSProfile({self.discovery_protocol})"
