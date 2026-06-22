from six.moves.builtins import list
from typing import Literal
from pydantic import BaseModel
from pydantic.fields import Field


class IPEndPoint(BaseModel):
    address: str = Field(
        description="IP address or hostname",
    )
    port: int = Field(
        description="Port number",
    )


class FastDDSDiscoveryType(str):
    SIMPLE = "simple"
    DISCOVERY_SERVER = "discovery_server"
    EASY = "easy"


class DiscoveryFastDDS(BaseModel):
    discovery_type: Literal["simple", "discovery_server", "easy"] = Field(
        default="discovery_server",
        description="Discovery mechanism to use: 'simple', 'discovery_server', or 'easy'.",
    )
    run_discovery_server: bool = Field(
        default=True,
        description="Run the discovery server.",
    )
    external_interfaces: list[str] = Field(
        default_factory=list,
        description="List of IP/host/interface addresses for connections to external networks.",
    )
    external_discovery_servers: list[IPEndPoint] = Field(
        default_factory=list,
        description="IP/host/interface of the discovery server.",
    )


class DiscoveryZenoh(BaseModel):
    with_router: bool = Field(default=True, description="Start the zenoh router")
    router_peers: list[str] = Field(
        default_factory=list,
        description="Remote router IPs/hostnames for mesh peering",
    )
    router_config: dict = Field(default_factory=dict, description="Router config overrides")
    session_config: dict = Field(default_factory=dict, description="Session config overrides")


class Discovery(BaseModel):
    middleware: Literal["fastdds", "zenoh"] = Field(
        default="zenoh",
        description="Middleware to use: 'fastdds' or 'zenoh'",
    )
    ros_domain_id: int = Field(
        default=0,
        description="ROS domain ID",
    )
    fastdds: DiscoveryFastDDS = Field(
        default_factory=DiscoveryFastDDS,
        description="Configuration for FastDDS discovery",
    )
    zenoh: DiscoveryZenoh = Field(
        default_factory=DiscoveryZenoh,
        description="Configuration for Zenoh discovery",
    )
