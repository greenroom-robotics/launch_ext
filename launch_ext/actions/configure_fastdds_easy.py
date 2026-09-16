from launch.action import Action
from launch.actions import SetEnvironmentVariable
from launch.launch_context import LaunchContext
from launch_ext.substitutions import ResolveHost


class ConfigureFastDDSEasyMode(Action):
    """
    Configure ROS 2 Easy Mode by setting the ROS2_EASY_MODE environment variable.

    This action sets up the ROS2_EASY_MODE environment variable to enable simplified
    ROS 2 communication. The easy mode base address is used by ROS 2 nodes to establish
    communication without complex DDS configuration.
    """

    def __init__(
        self,
        easy_mode_base_address: str = "0.0.0.0",
        **kwargs,
    ):
        """
        Initialize the ConfigureFastDDSEasyMode action.

        Args:
            easy_mode_base_address (str): Base address for ROS 2 Easy Mode communication.
                Defaults to "0.0.0.0"
            **kwargs: Additional arguments passed to the parent Action class
        """
        super().__init__(**kwargs)

        self.actions = [
            SetEnvironmentVariable(
                "ROS2_EASY_MODE",
                ResolveHost(easy_mode_base_address),
            )
        ]

    def execute(self, context: LaunchContext) -> None:
        """
        Execute all configured actions in sequence.

        This method is called by the launch system when the action is executed.
        It iterates through all the actions created during initialization and
        executes them in order.

        Args:
            context (LaunchContext): The launch context

        Returns:
            None
        """
        for action in self.actions:
            action.execute(context)

        return None
