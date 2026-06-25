from dataclasses import dataclass
from typing import Literal, Optional

import launch.logging
from launch.action import Action
from launch.actions import OpaqueFunction
from launch.launch_context import LaunchContext

from ..discovery.avahi_manager import AvahiServiceManager


@dataclass
class AvahiProductService:
    """Configuration for a single Avahi product service."""

    product: str
    port: int
    protocol: Literal["http", "https"] = "http"
    path: str = "/"
    display_name: Optional[str] = None


class ConfigureAvahi(Action):
    """
    Configure Avahi mDNS/DNS-SD service advertisements for ROS 2 launch.

    This action connects to the Avahi daemon via D-Bus and registers mDNS
    services for network discovery. The services remain advertised for the
    lifetime of the launch.

    Example usage in a launch file:
        from launch_ext.actions import ConfigureAvahi, AvahiProductService

        ConfigureAvahi(
            services=[
                AvahiProductService(
                    product="myproduct",
                    port=8080,
                    protocol="http",
                    path="/api",
                    display_name="My Robot",
                ),
                AvahiProductService(
                    product="otherproduct",
                    port=443,
                    protocol="https",
                ),
            ]
        )
    """

    def __init__(
        self,
        services: list[AvahiProductService],
        **kwargs,
    ):
        """
        Initialize the ConfigureAvahi action.

        Args:
            services: List of AvahiProductService objects to advertise
            **kwargs: Additional arguments passed to the parent Action class
        """
        super().__init__(**kwargs)

        self._services = services

        # Create the opaque function action for registration
        self._register_action = OpaqueFunction(function=self._register_services)

    def _register_services(self, context: LaunchContext, *_args, **_kwargs) -> list[Action]:
        """
        Register the configured Avahi services.

        This function is called during launch execution to connect to Avahi
        and register the configured services.

        Args:
            context: The launch context
            *_args: Unused positional arguments
            **_kwargs: Unused keyword arguments

        Returns:
            Empty list (no additional actions to execute)
        """
        logger = launch.logging.get_logger("launch.user")
        manager = AvahiServiceManager()

        try:
            manager.connect()

            for service in self._services:
                manager.create_product_service(
                    product=service.product,
                    port=service.port,
                    protocol=service.protocol,
                    path=service.path,
                    display_name=service.display_name,
                )

            registered = manager.list_services()
            logger.info(f"Registered Avahi services: {registered}")

        except Exception as e:
            logger.warning(f"Failed to register Avahi service (mDNS discovery disabled): {e}")
            return []

        # Store manager reference in context to keep services alive during launch lifetime
        context.extend_locals({"avahi_manager": manager})
        return []

    def execute(self, context: LaunchContext) -> None:
        """
        Execute the Avahi configuration action.

        This method is called by the launch system when the action is executed.
        It registers the configured Avahi services.

        Args:
            context: The launch context

        Returns:
            None
        """
        self._register_action.execute(context)
        return None
