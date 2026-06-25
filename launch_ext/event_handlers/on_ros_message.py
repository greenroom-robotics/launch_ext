from typing import Callable, Optional

from launch.event import Event
from launch.event_handler import BaseEventHandler
from launch.launch_context import LaunchContext
from launch.some_entities_type import SomeEntitiesType

from ..events import ROSMessageReceived


class OnROSMessage(BaseEventHandler):
    """Handle :class:`~launch_ext.events.ROSMessageReceived` events for one topic.

    Matches only events whose ``topic`` equals the configured topic, then calls
    ``on_message(event, context)`` and returns whatever entities it produces, so
    the policy of "what to do with this message" lives in the caller, not here.
    """

    def __init__(
        self,
        *,
        topic: str,
        on_message: Callable[[ROSMessageReceived, LaunchContext], Optional[SomeEntitiesType]],
        **kwargs,
    ) -> None:
        """Create an OnROSMessage event handler."""
        self.__topic = topic
        self.__on_message = on_message
        super().__init__(
            matcher=lambda event: (isinstance(event, ROSMessageReceived) and event.topic == topic),
            **kwargs,
        )

    def handle(self, event: Event, context: LaunchContext) -> Optional[SomeEntitiesType]:
        """Handle the event by delegating to the ``on_message`` callback."""
        super().handle(event, context)
        return self.__on_message(event, context)

    @property
    def handler_description(self) -> str:
        return f"{self.__on_message}"

    @property
    def matcher_description(self) -> str:
        return f"event == ROSMessageReceived and event.topic == '{self.__topic}'"
