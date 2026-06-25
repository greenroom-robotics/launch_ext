from typing import Any

from launch.action import Action
from launch.event import Event


class Restart(Event):
    """Event requesting that a :class:`~launch_ext.actions.Restartable` restart.

    ``action`` identifies which restartable action should handle this event (the
    handler matches on it, mirroring the ``event.action`` convention used by
    ``launch``'s :class:`OnActionEventBase`). Any extra keyword arguments are
    stored on :attr:`payload` and forwarded to the action's factory so a restart
    can be parameterised (e.g. ``recording_config_dir``).
    """

    name = "launch_ext.events.Restart"

    def __init__(self, *, action: Action, **payload: Any) -> None:
        """Create a Restart event targeting ``action`` with an optional payload."""
        self.__action = action
        self.__payload = payload

    @property
    def action(self) -> Action:
        """Getter for the target action."""
        return self.__action

    @property
    def payload(self) -> dict:
        """Getter for the restart payload (extra keyword arguments)."""
        return self.__payload
