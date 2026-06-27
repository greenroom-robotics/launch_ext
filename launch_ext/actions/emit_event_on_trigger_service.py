from typing import Any, Callable, Union

from launch.event import Event
from launch.launch_context import LaunchContext

from .serve_ros_service import ServeROSService

EventOrFactory = Union[Event, Callable[[], Event]]


class EmitEventOnTriggerService(ServeROSService):
    """Emit a launch event whenever a ``std_srvs/srv/Trigger`` service is called.

    Offers a ``Trigger`` service at ``service_name``; each call emits ``event``
    onto the launch event loop and returns a successful response. ``event`` may be
    an :class:`~launch.event.Event` instance (emitted as-is each time) or a
    zero-argument callable returning a fresh event per call — handy when the event
    must not be shared between emissions.
    """

    def __init__(
        self,
        *,
        service_name: str,
        event: EventOrFactory,
        success_message: str = "",
        **kwargs,
    ) -> None:
        """Create an EmitEventOnTriggerService action."""
        # Imported lazily so importing launch_ext does not require std_srvs.
        from std_srvs.srv import Trigger

        super().__init__(
            srv_type=Trigger,
            service_name=service_name,
            callback=self._on_trigger,
            **kwargs,
        )
        self._event = event
        self._success_message = success_message

    def _on_trigger(self, request: Any, response: Any, context: LaunchContext) -> Any:
        event = self._event() if callable(self._event) else self._event
        context.asyncio_loop.call_soon_threadsafe(context.emit_event_sync, event)
        response.success = True
        response.message = self._success_message
        return response
