from typing import Literal
from pydantic import BaseModel
from pydantic.fields import Field


class DiscoverySimple(BaseModel):
    own_ip: str = Field(
        default="0.0.0.0",
        description="IP/host/interface address of the primary network interface. This is where DDS traffic will route to.",
    )


class DiscoveryFastDDS(BaseModel):
    with_discovery_server: bool = Field(
        default=True,
        description="Run the discovery server. It will bind to 0.0.0.0:11811",
    )
    discovery_server_ip: str = Field(
        default="0.0.0.0",
        description="IP/host/interface of the discovery server. Assumes port of 11811",
    )
    allowed_interfaces: list[str] = Field(
        default_factory=list,
        description="List of IP/host/interface addresses to allow. First is used as primary. Empty means all interfaces.",
    )


class DiscoveryZenoh(BaseModel):
    with_router: bool = Field(default=True, description="Start the zenoh router")
    router_peers: list[str] = Field(
        default_factory=list,
        description="Remote router IPs/hostnames for mesh peering",
    )
    router_config: dict = Field(default_factory=dict, description="Router config overrides")
    session_config: dict = Field(default_factory=dict, description="Session config overrides")


class DiscoveryEasy(BaseModel):
    base_address: str = Field(
        default="127.0.0.1",
        description="Base address for easy discovery",
    )


class Discovery(BaseModel):
    type: Literal["simple", "fastdds", "zenoh", "easy"] = Field(
        default="zenoh",
        description="Discovery mechanism to use: 'simple', 'fastdds', 'zenoh', or 'easy'",
    )
    ros_domain_id: int = Field(
        default=0,
        description="ROS domain ID",
    )
    simple: DiscoverySimple = Field(
        default_factory=DiscoverySimple,
        description="Configuration for simple discovery",
    )
    fastdds: DiscoveryFastDDS = Field(
        default_factory=DiscoveryFastDDS,
        description="Configuration for FastDDS discovery",
    )
    zenoh: DiscoveryZenoh = Field(
        default_factory=DiscoveryZenoh,
        description="Configuration for Zenoh discovery",
    )
    easy: DiscoveryEasy = Field(
        default_factory=DiscoveryEasy,
        description="Configuration for easy discovery",
    )
