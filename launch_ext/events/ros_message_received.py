from typing import Any

from launch.event import Event


class ROSMessageReceived(Event):
    """Event emitted when a bridged ROS subscription receives a message.

    Carries the topic it arrived on and the deserialised message so that
    handlers (e.g. :class:`launch_ext.event_handlers.OnROSMessage`) can filter
    by topic and act on the payload.
    """

    name = "launch_ext.events.ROSMessageReceived"

    def __init__(self, *, topic: str, msg: Any) -> None:
        """Create a ROSMessageReceived event."""
        self.__topic = topic
        self.__msg = msg

    @property
    def topic(self) -> str:
        """Getter for the topic the message arrived on."""
        return self.__topic

    @property
    def msg(self) -> Any:
        """Getter for the received message."""
        return self.__msg
