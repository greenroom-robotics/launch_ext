from typing import Any, Callable, Optional, Union, cast

from launch.action import Action
from launch.event import Event
from launch.event_handlers.on_action_event_base import OnActionEventBase
from launch.launch_context import LaunchContext
from launch.some_entities_type import SomeEntitiesType

from ..events import Restart


class OnRestart(OnActionEventBase):
    """Handle :class:`~launch_ext.events.Restart` events for a given action.

    May be configured to only handle restarts targeting a specific action
    (``target_action``), or — when omitted — every restart event. Mirrors the
    style of :class:`launch_ext.event_handlers.OnActionReady`.
    """

    def __init__(
        self,
        *,
        target_action: Union[Callable[["Action"], bool], "Action"] | None = None,
        on_restart: SomeEntitiesType | Callable[[Restart, LaunchContext], SomeEntitiesType | None],
        **kwargs: Any,
    ) -> None:
        """Create an OnRestart event handler."""
        on_restart = cast(
            Union[SomeEntitiesType, Callable[[Event, LaunchContext], Optional[SomeEntitiesType]]],
            on_restart,
        )
        super().__init__(
            action_matcher=target_action,
            on_event=on_restart,
            target_event_cls=Restart,
            target_action_cls=Action,
            **kwargs,
        )
