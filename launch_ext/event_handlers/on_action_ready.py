from collections.abc import Callable
from typing import cast
from typing import Optional
from typing import Union
from typing import Any

from launch.action import Action
from launch.event import Event
from launch.launch_context import LaunchContext
from launch.some_entities_type import SomeEntitiesType
from launch.event_handlers.on_action_event_base import OnActionEventBase

from ..events import ActionReady


class OnActionReady(OnActionEventBase):
    """
    Convenience class for handling an action ready event.

    It may be configured to only handle the readiness of a specific action,
    or to handle them all.
    """

    def __init__(
        self,
        *,
        target_action: Union[Callable[["Action"], bool], "Action"] | None = None,
        on_ready: (
            SomeEntitiesType | Callable[[ActionReady, LaunchContext], SomeEntitiesType | None]
        ),
        **kwargs: Any
    ) -> None:
        """Create an OnActionReady event handler."""
        on_ready = cast(
            Union[SomeEntitiesType, Callable[[Event, LaunchContext], Optional[SomeEntitiesType]]],
            on_ready,
        )
        super().__init__(
            action_matcher=target_action,
            on_event=on_ready,
            target_event_cls=ActionReady,
            target_action_cls=Action,
            handle_once=True,
            **kwargs,
        )
