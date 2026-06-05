from launch.action import Action
from launch.event import Event


class ActionReady(Event):
    """Event that is emitted when an action is ready."""

    name = "launch_ext.events.ActionReady"

    def __init__(self, *, action: Action) -> None:
        """Create an ActionReady event."""
        self.__action = action

    @property
    def action(self) -> Action:
        """Getter for action."""
        return self.__action
