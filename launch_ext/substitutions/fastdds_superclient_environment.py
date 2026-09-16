import os

from launch.substitutions import LaunchConfiguration
from launch.substitution import Substitution
import launch.logging
from .fastdds_env_var import get_fastdds_default_profile_env_var


class FastDDSSuperclientEnvironment(Substitution):
    """Substitution that provides the FastDDS SuperClient profile path.

    Use this in a Node's environment parameter to configure SuperClient mode.
    """

    def __init__(
        self,
        discovery_mode: str,
        fastdds_superclient_profile_path: str | None = None,
    ):
        """Initialize the FastDDSSuperclientEnvironment substitution.

        Args:
            fastdds_superclient_profile_path (str | None): Path to the FastDDS SuperClient profile file.
                Will default to LaunchConfiguration("fastdds_profile_super_client")
            discovery_mode (str | None): Discovery mode the application is running in
        """
        self.profile_path = (
            fastdds_superclient_profile_path
            if fastdds_superclient_profile_path is not None
            else LaunchConfiguration("fastdds_profile_super_client")
        )
        self.logger = launch.logging.get_logger("launch.user.fastdds_superclient_environment")
        self.discovery_mode = discovery_mode

    def perform(self, context):
        """Return the profile path or empty string if using easy mode."""
        if self.discovery_mode == "easy" or os.getenv("ROS2_EASY_MODE"):
            self.logger.info(
                "Using easymode dds, skipping FastDDS SuperClient profile configuration."
            )
            return ""

        if isinstance(self.profile_path, Substitution):
            return self.profile_path.perform(context)
        return self.profile_path

    def describe(self):
        return f"FastDDSSuperclientEnvironment(profile_path={self.profile_path})"


def get_fastdds_superclient_environment(
    discovery_mode: str, fastdds_superclient_profile_path: str | None = None
) -> dict:
    """Returns environment dict for SuperClient nodes.

    Args:
        discovery_mode: Discovery mode the application is running in
        fastdds_superclient_profile_path: Optional custom path to profile file

    Returns:
        Dictionary with environment variables for superclient configuration

    Example:
        Node(
            package='my_pkg',
            executable='my_node',
            environment=get_fastdds_superclient_environment(discovery_mode="fastdds")
        )
    """

    if discovery_mode == "easy" or os.getenv("ROS2_EASY_MODE"):
        return {}

    return {
        get_fastdds_default_profile_env_var(): FastDDSSuperclientEnvironment(
            discovery_mode, fastdds_superclient_profile_path
        )
    }
