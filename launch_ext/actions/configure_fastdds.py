import pathlib

from launch.action import Action
from launch.launch_context import LaunchContext
from launch.launch_description_entity import LaunchDescriptionEntity

from launch.actions import (
    EmitEvent,
    ExecuteProcess,
    SetLaunchConfiguration,
    SetEnvironmentVariable,
)
from launch.substitutions import (
    LaunchConfiguration,
)
from .write_file import WriteFile
from .execute_after_process_output import ExecuteAfterProcessOutput
from ..substitutions import (
    FastDDSProfile,
    get_fastdds_default_profile_env_var,
)
from ..events import ActionReady

from ..discovery.discovery_config import IPEndPoint, DEFAULT_FAST_DISCOVERY_SERVER_PORT



class FastDDSDiscoveryServer(Action):
    """
    Configure Fast DDS Discovery Server with the specified external interfaces and discovery servers, and start the server process.
    """

    def __init__(
        self,
        external_interfaces: list[str] | None = None,
        external_discovery_servers: list[IPEndPoint] | None = None,
        local_discovery_server: IPEndPoint = IPEndPoint(address="127.0.0.1", port=DEFAULT_FAST_DISCOVERY_SERVER_PORT),
        server_id: str = "0",
        domain_id: int | None = None,
        fastdds_profile_path_dir: str | pathlib.Path | None = None,
        **kwargs,
    ):
        """
        Initialize the FastDDSDiscoveryServer action.

        Args:
            external_interfaces (list[str]): List of interfaces that are expected to be used for cross-host communication. First is used as primary. Empty means only intra-host communication.
            external_discovery_servers (list[IPEndPoint]): List of external discovery servers to connect to.
            fastdds_profile_path_dir (str | pathlib.Path): Optional prefix path for the generated Fast DDS profile XML files. If not provided, defaults to the user's home directory.
            domain_id (int): Optional ROS domain ID to set in the Fast DDS profiles.
            **kwargs: Additional arguments passed to the parent Action class
        """
        super().__init__(**kwargs)
        if external_interfaces is None:
            external_interfaces = []

        self.discovery_server: ExecuteProcess | None = None

        fastdds_profile_path_dir = (
            pathlib.Path(fastdds_profile_path_dir)
            if fastdds_profile_path_dir
            else pathlib.Path.home()
        )

        fastdds_discovery_server_path = LaunchConfiguration(
            "fastdds_discovery_server_profile",
            default=str(fastdds_profile_path_dir / "fastdds_server_profile.xml"),
        )

        write_fastdds_discovery_server = WriteFile(
            FastDDSProfile(
                discovery_protocol="SERVER",
                local_discovery_server=local_discovery_server,
                external_interfaces=external_interfaces,
                external_discovery_servers=external_discovery_servers,
                domain_id=domain_id,
            ),
            LaunchConfiguration("fastdds_discovery_server_profile"),
        )

        self.discovery_server = ExecuteProcess(
            name="discovery_server",
            cmd=[
                "fast-discovery-server",
                "42",  # 42 means start server, run this directly so SIGINT works properly to shut it down
                "-i",
                server_id,
                "-x",
                LaunchConfiguration("fastdds_discovery_server_profile"),
            ],
            output={"both": ["screen", "log"]},
        )

        ready_emitter = ExecuteAfterProcessOutput(
            target=self.discovery_server,
            match=b"Running on:",
            then=EmitEvent(event=ActionReady(action=self.discovery_server))
        )

        self.actions = [
            SetLaunchConfiguration(
                "fastdds_discovery_server_profile", fastdds_discovery_server_path
            ),
            write_fastdds_discovery_server,
            self.discovery_server,
            ready_emitter,
        ]

    def execute(self, context: LaunchContext) -> list[LaunchDescriptionEntity]:
        return self.actions


class ConfigureFastDDS(Action):
    """
    Configure Fast DDS middleware for ROS 2 nodes with support for different discovery protocols.

    This class sets up the Fast DDS configuration profile and optionally starts a Discovery Server
    process based on the provided parameters. It creates configuration XML files and sets the
    appropriate environment variables to use these configurations.

    The class supports three discovery protocols:
    - SIMPLE: Direct peer-to-peer discovery (standard DDS discovery)
    - CLIENT: Discovery Server client mode (clients connect to a discovery server)
    - SERVER: Discovery Server mode

    """

    def __init__(
        self,
        discovery_protocol: str = "CLIENT",
        external_interfaces: list[str] | None = None,
        local_discovery_server: IPEndPoint = IPEndPoint(address="127.0.0.1", port=DEFAULT_FAST_DISCOVERY_SERVER_PORT),
        shm_large_segment: bool = False,
        domain_id: int | None = None,
        fastdds_profile_path_dir=None,
        **kwargs,
    ):
        """
        Initialize the ConfigureFastDDS action.

        Args:
            fastdds_profile_path (str, optional): Path where to write the main Fast DDS profile.
                Defaults to "~/fastdds_profile.xml"
            **kwargs: Additional arguments passed to the parent Action class
        """
        super().__init__(**kwargs)
        external_interfaces = external_interfaces if external_interfaces is not None else []

        fastdds_profile_path_dir = (
            pathlib.Path(fastdds_profile_path_dir)
            if fastdds_profile_path_dir
            else pathlib.Path.home()
        )

        fastdds_local_profile_path = LaunchConfiguration(
            "fastdds_profile_path",
            default=str(fastdds_profile_path_dir / "fastdds_profile.xml"),
        )

        write_fastdds_local_profile = WriteFile(
            FastDDSProfile(
                discovery_protocol=discovery_protocol,
                local_discovery_server=local_discovery_server,
                external_interfaces=external_interfaces,
                shm_large_segment=shm_large_segment,
                domain_id=domain_id,
            ),
            LaunchConfiguration("fastdds_profile"),
        )

        # Collect all actions to be executed when this Action is executed
        self.actions = [
            # Set launch configurations for profile paths
            SetLaunchConfiguration("fastdds_profile", fastdds_local_profile_path),
            # Write the configuration files
            write_fastdds_local_profile,
            # Configure environment to use the main profile
            SetEnvironmentVariable(
                get_fastdds_default_profile_env_var(),
                LaunchConfiguration("fastdds_profile"),
            ),
        ]

    def execute(self, context: LaunchContext) -> list[LaunchDescriptionEntity]:
        return self.actions
