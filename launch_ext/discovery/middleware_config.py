from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from enum import Enum
from typing import Any


class LabelledStrEnum(str, Enum):
    """str enum where each member is ``(value, label)``.

    The label is exported as ``oneOf[].title`` in the JSON schema so RJSF
    dropdowns render the friendly name instead of the raw string value.
    """

    label: str

    def __new__(cls, value: str, label: str) -> "LabelledStrEnum":
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        return obj

    def __str__(self) -> str:
        return self.value

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _source: Any, _handler: Any
    ) -> dict[str, Any]:  # noqa: ARG003
        return {
            # "title": re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", cls.__name__),
            "type": "string",
            "oneOf": [{"const": m.value, "title": m.label} for m in cls],
        }

DEFAULT_FAST_DISCOVERY_SERVER_PORT = 11811


class IPEndPoint(BaseModel):
    model_config = ConfigDict(title="IP Endpoint")

    address: str = Field(
        description="IP address or hostname",
    )
    port: int = Field(
        description="Port number",
    )


class MiddlewareTypes(LabelledStrEnum):
    FASTDDS = "fastdds", "FastDDS"
    ZENOH = "zenoh", "Zenoh"


class FastDDSDiscoveryType(LabelledStrEnum):
    SIMPLE = "simple", "Simple"
    DISCOVERY_SERVER = "discovery_server", "Discovery Server"
    EASY = "easy", "Easy"


class FastDDSMiddleware(BaseModel):
    model_config = ConfigDict(title="FastDDS")
    discovery_type: FastDDSDiscoveryType = Field(
        default=FastDDSDiscoveryType.DISCOVERY_SERVER,
        title="Discovery Mechanism",
        description="Discovery mechanism to use: 'simple', 'discovery_server', or 'easy'.",
    )
    run_discovery_server: bool = Field(
        default=True,
        title="Run Discovery Server",
        description="Run the discovery server.",
    )
    local_discovery_server: IPEndPoint | None = Field(
        default_factory=lambda: IPEndPoint(
            address="127.0.0.1", port=DEFAULT_FAST_DISCOVERY_SERVER_PORT
        ),
        title="Local Discovery Server Endpoint",
        description="Local discovery server endpoint.",
    )
    external_interfaces: list[str] = Field(
        default_factory=list,
        title="External Interfaces",
        description="List of interfaces that are expected to be used for cross-host communication. Empty means only intra-host communication.",
    )
    external_discovery_servers: list[IPEndPoint] = Field(
        default_factory=list,
        title="External Discovery Servers",
        description="List of external discovery server endpoints to connect to.",
    )

    @field_validator("external_interfaces")
    def validate_interfaces_for_lo(cls, external_interfaces):
        if any(
            interface in ["0.0.0.0", "localhost", "127.0.0.1"] for interface in external_interfaces
        ):
            raise ValueError(
                "Using loopback is not valid for external_interfaces, please only define specific interfaces or leave empty for no external interfaces."
            )
        return external_interfaces

    @field_validator("external_discovery_servers")
    def validate_discovery_servers_for_lo(cls, external_discovery_servers):
        if any(
            server.address in ["0.0.0.0", "localhost", "127.0.0.1"] for server in external_discovery_servers
        ):
            raise ValueError(
                "Using loopback is not valid for external_discovery_servers, please only define specific interfaces or leave empty for no external discovery servers."
            )
        return external_discovery_servers


class ZenohMiddleware(BaseModel):
    model_config = ConfigDict(title="Zenoh")

    run_router: bool = Field(
        default=True,
        title="Run Router",
        description="Start a Zenoh router.",
    )
    router_peers: list[str] = Field(
        default_factory=list,
        title="Router Peers",
        description="Remote Zenoh routers to peer with.",
    )
    router_config: dict = Field(
        default_factory=dict,
        title="Router Config Overrides",
        description="Deep-merged into the Zenoh router config.",
    )
    session_config: dict = Field(
        default_factory=dict,
        title="Session Config Overrides",
        description="Deep-merged into the Zenoh session config.",
    )


class MiddlewareConfig(BaseModel):
    model_config = ConfigDict(title="Middleware")

    middleware: MiddlewareTypes = Field(
        default=MiddlewareTypes.FASTDDS,
        title="Middleware",
        description="Middleware to use: 'fastdds' or 'zenoh'",
    )
    ros_domain_id: int = Field(
        default=0,
        title="ROS Domain ID",
        description="The `ROS_DOMAIN_ID` env var. Must match across all peers.",
    )
    fastdds: FastDDSMiddleware = Field(default_factory=FastDDSMiddleware)
    zenoh: ZenohMiddleware = Field(default_factory=ZenohMiddleware)
