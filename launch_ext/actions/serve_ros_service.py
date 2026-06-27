from typing import Any, Callable

from launch.action import Action
from launch.launch_context import LaunchContext

ServiceCallback = Callable[[Any, Any, LaunchContext], Any]


class ServeROSService(Action):
    """Offer a ROS service on the shared launch_ros node and dispatch to a callback.

    On execution this creates a service on the in-process node managed by
    ``launch_ros`` (``get_ros_node``). Each request invokes
    ``callback(request, response, context)`` on the ``launch_ros`` executor
    thread; the callback fills in and returns the response. To affect the launch
    run (e.g. emit an event) hand work back to the launch loop with
    ``context.asyncio_loop.call_soon_threadsafe`` — the same hand-off pattern used
    by :class:`~launch_ext.actions.SubscribeRosTopic`.
    """

    def __init__(
        self,
        *,
        srv_type: type,
        service_name: str,
        callback: ServiceCallback,
        **kwargs,
    ) -> None:
        """Create a ServeROSService action.

        :param srv_type: the ROS service class to offer.
        :param service_name: the service name to offer.
        :param callback: ``(request, response, context) -> response`` invoked for
            each request, on the launch_ros executor thread.
        """
        super().__init__(**kwargs)
        self._srv_type = srv_type
        self._service_name = service_name
        self._callback = callback
        self._service = None

    def execute(self, context: LaunchContext) -> None:
        """Create the service on the shared launch_ros node."""
        # Imported lazily so unit tests of callbacks don't require launch_ros/rclpy.
        from launch_ros.ros_adapters import get_ros_node

        node = get_ros_node(context)
        self._service = node.create_service(
            self._srv_type,
            self._service_name,
            lambda request, response: self._callback(request, response, context),
        )
        return None
