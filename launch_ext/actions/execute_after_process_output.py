"""Module for the ExecuteAfterProcessOutput action."""

from typing import List, Optional

import launch.logging
from launch.action import Action
from launch.actions import RegisterEventHandler, ExecuteProcess
from launch.event_handlers import OnProcessIO
from launch.launch_context import LaunchContext
from launch.some_entities_type import SomeEntitiesType

from launch.launch_description_entity import LaunchDescriptionEntity


class ExecuteAfterProcessOutput(Action):
    """Defer action[s] until a target process emits a matching stdout line.

    The wrapped actions are visited by the launch system the first time
    ``match`` is found in the target process's stdout. Subsequent matches are
    ignored.
    """

    def __init__(
        self,
        *,
        target: ExecuteProcess,
        match: bytes,
        then: SomeEntitiesType,
        handle_once: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._target = target
        self._match = match
        self._then = then
        self._handle_once = handle_once
        self._event_handler = None
        self._fired = False
        self._logger = launch.logging.get_logger("launch.user")

    def _on_stdout(self, info):
        if self._fired:
            return None
        if self._match in info.text:
            self._fired = True
            self._logger.info(
                f"ExecuteAfterProcessOutput matched {self._match!r}; running deferred action(s)"
            )
            if self._handle_once:
                pass  # TODO: Unregister event handler to avoid handling future matches
            return self._then
        return None

    def execute(self, context: LaunchContext) -> List[LaunchDescriptionEntity]:
        evt_handler = RegisterEventHandler(
            OnProcessIO(target_action=self._target, on_stdout=self._on_stdout)
        )
        return [evt_handler]
