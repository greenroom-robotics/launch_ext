from pathlib import Path
from launch.substitutions import (
    PathJoinSubstitution,
    FileContent,
)
from launch_ros.substitutions import FindPackageShare
from launch.action import Action
from launch.actions import (
    ExecuteProcess,
    OpaqueFunction,
    RegisterEventHandler,
    SetEnvironmentVariable,
)
from launch.event_handlers import OnProcessStart
from launch.events.process import ProcessStarted
from launch.launch_context import LaunchContext
from launch_ros.actions import Node
import json
import launch.logging
from typing import List, Optional
from launch.launch_description_entity import LaunchDescriptionEntity



def deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge two dictionaries, with override values taking precedence.

    Args:
        base (dict): The base dictionary
        override (dict): The override dictionary whose values take precedence

    Returns:
        dict: A new dictionary with merged values
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = deep_merge(result[key], value)
        else:
            # For all other types (including lists), override completely replaces base
            result[key] = value

    return result


class ConfigureZenoh(Action):
    """
    Configure Zenoh middleware for ROS 2 nodes.

    This action configures Zenoh middleware using modern rmw_zenoh best practices.
    By default, it relies on rmw_zenoh's built-in defaults. Use ZENOH_CONFIG_OVERRIDE
    environment variable at the container level for runtime configuration.
    Optionally generates custom configuration files and starts a Zenoh router process.
    """

    def write_config_file(
        self, context: LaunchContext, file_name: str, overrides: dict, destination: str
    ) -> None:
        """
        Read a JSON config file, apply overrides, and write the result to a new location.

        This helper method reads a JSON configuration file from the package share directory,
        applies any overrides provided as a dictionary, and writes the resulting configuration
        to a new file in the /home/ros directory.

        Args:
            context (LaunchContext): The launch context
            file_name (str): Name of the configuration file to read and write
            overrides (dict, optional): Dictionary of settings to override in the config file.
                Defaults to {}.

        Returns:
            None
        """
        # Read the content of the template configuration file
        content = FileContent(
            PathJoinSubstitution([FindPackageShare("launch_ext"), "config", file_name])
        ).perform(context)

        # Parse the JSON content and apply overrides
        content_json = json.loads(content)
        content_json = deep_merge(content_json, overrides)

        # Write the modified configuration to the destination
        with open(destination, "w") as f:
            json.dump(content_json, f, indent=4)

        # Log the action
        launch.logging.get_logger("launch.user").info(f"Wrote file '{destination}'.")

        return None

    def __init__(
        self,
        run_router: bool = False,
        router_config: Optional[dict] = None,
        session_config: Optional[dict] = None,
        generate_router_config_file: bool = False,
        generate_session_config_file: bool = False,
        zenoh_router_config_path: Optional[str] = None,
        zenoh_session_config_path: Optional[str] = None,
        inherit: bool = False,
        **kwargs,
    ):
        """
        Initialize the ConfigureZenoh action.

        Args:
            run_router (bool): Whether to start a Zenoh router process
            router_config (dict, optional): Configuration overrides for the Zenoh router
                (only used if generate_router_config_file=True)
            session_config (dict, optional): Configuration overrides for the Zenoh session
                (only used if generate_session_config_file=True)
            generate_router_config_file (bool): Whether to generate router config file
                (default False, uses rmw_zenoh defaults)
            generate_session_config_file (bool): Whether to generate session config file
                (default False, uses rmw_zenoh defaults)
            zenoh_router_config_path (str): Path where to write the Zenoh router config
            zenoh_session_config_path (str): Path where to write the Zenoh session config
            **kwargs: Additional arguments passed to the parent Action class

        Note:
            For runtime configuration changes, set ZENOH_CONFIG_OVERRIDE environment
            variable at the container/system level instead of using config files.
        """
        super().__init__(**kwargs)

        # Handle mutable default arguments
        if router_config is None:
            router_config = {}
        if session_config is None:
            session_config = {}
        if zenoh_router_config_path is None:
            zenoh_router_config_path = str(Path.home() / "zenoh_router_config.json")
        if zenoh_session_config_path is None:
            zenoh_session_config_path = str(Path.home() / "zenoh_session_config.json")

        # Collect the actions to be executed
        self.actions = []

        # Set environment variable to use the generated session config
        self.actions.append(SetEnvironmentVariable(
            name="ZENOH_SESSION_CONFIG_URI", value=zenoh_session_config_path
        ))

        # Conditionally create configuration file actions
        if generate_router_config_file:
            write_zenoh_router_config = OpaqueFunction(
                function=self.write_config_file,
                kwargs={
                    "file_name": "zenoh_router_config.json",
                    "overrides": router_config,
                    "destination": zenoh_router_config_path,
                },
            )
            self.actions.append(write_zenoh_router_config)

        if generate_session_config_file:
            write_zenoh_session_config = OpaqueFunction(
                function=self.write_config_file,
                kwargs={
                    "file_name": "zenoh_session_config.json",
                    "overrides": session_config,
                    "destination": zenoh_session_config_path,
                },
            )
            self.actions.append(write_zenoh_session_config)

        # Conditionally add the router node to the actions
        if run_router:
            zenoh_router = Node(
                name="zenoh_router",
                package="rmw_zenoh_cpp",
                executable="rmw_zenohd",
                output="both",
            )

            # Set environment variable to use the generated router config
            self.actions.append(SetEnvironmentVariable(
                name="ZENOH_ROUTER_CONFIG_URI", value=zenoh_router_config_path
            ))

            def renice_router(
                event: ProcessStarted, _context: LaunchContext
            ) -> List[ExecuteProcess]:
                return [
                    ExecuteProcess(
                        cmd=["sudo", "renice", "-n", "-20", "-p", str(event.pid)],
                        name="renice_zenoh_router",
                        output="both",
                    )
                ]

            # Renice the router process once it has started
            self.actions.append(
                RegisterEventHandler(
                    OnProcessStart(target_action=zenoh_router, on_start=renice_router)
                )
            )
            self.actions.append(zenoh_router)

    def execute(self, context: LaunchContext) -> list[LaunchDescriptionEntity]:
        return self.actions
