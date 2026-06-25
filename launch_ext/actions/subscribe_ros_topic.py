from typing import Any, Callable, Optional

from launch.action import Action
from launch.event import Event
from launch.launch_context import LaunchContext

from ..events import ROSMessageReceived

EventFactory = Callable[[str, Any], Event]


class SubscribeRosTopic(Action):
    """Bridge a ROS topic into the launch event system.

    On execution this creates a subscription on the in-process node managed by
    ``launch_ros`` (``get_ros_node``). Each received message is turned into a
    launch event (a :class:`~launch_ext.events.ROSMessageReceived` by default)
    and emitted onto the launch event loop, where handlers such as
    :class:`~launch_ext.event_handlers.OnROSMessage` can act on it.

    The subscription callback runs on the ``launch_ros`` executor thread, so the
    event is handed back to the launch loop with ``call_soon_threadsafe`` — the
    same hand-off pattern used by ``launch_ros``'s ``ROSTimer``.
    """

    def __init__(
        self,
        *,
        msg_type: type,
        topic: str,
        qos: Any = 10,
        event_factory: Optional[EventFactory] = None,
        **kwargs,
    ) -> None:
        """Create a SubscribeRosTopic action.

        :param msg_type: the ROS message class to subscribe with.
        :param topic: the topic name to subscribe to.
        :param qos: a QoS profile or history depth (passed straight to
            ``create_subscription``).
        :param event_factory: optional ``(topic, msg) -> Event`` used to build the
            launch event; defaults to :class:`~launch_ext.events.ROSMessageReceived`.
        """
        super().__init__(**kwargs)
        self._msg_type = msg_type
        self._topic = topic
        self._qos = qos
        self._event_factory: EventFactory = event_factory or (
            lambda topic, msg: ROSMessageReceived(topic=topic, msg=msg)
        )
        self._subscription = None

    def execute(self, context: LaunchContext) -> None:
        """Create the subscription on the shared launch_ros node."""
        # Imported lazily so unit tests of the message hand-off don't require
        # launch_ros/rclpy to be importable.
        from launch_ros.ros_adapters import get_ros_node

        node = get_ros_node(context)
        self._subscription = node.create_subscription(
            self._msg_type,
            self._topic,
            lambda msg: self._handle_message(context, msg),
            self._qos,
        )
        return None

    def _handle_message(self, context: LaunchContext, msg: Any) -> None:
        """Turn a received message into a launch event on the launch loop thread."""
        event = self._event_factory(self._topic, msg)
        context.asyncio_loop.call_soon_threadsafe(context.emit_event_sync, event)
