"""Module for the StaggeredExecute action."""

from typing import Iterable
from typing import List

from launch.action import Action
from launch.actions import ExecuteLocal, TimerAction
from launch.launch_context import LaunchContext
from launch.launch_description_entity import LaunchDescriptionEntity


class StaggeredExecute(Action):
    """Stagger process startup by wrapping each process in a TimerAction.

    Each process-launching action in ``entities`` is delayed by
    ``process_index * interval`` seconds, where ``process_index`` counts only
    process actions (starting at 0). Non-process entities pass through unchanged
    and fire immediately. The first process (offset 0) is yielded unwrapped so it
    starts synchronously. Operates on the top-level list only (no recursion into
    container actions).

    ``ExecuteProcess`` subclasses ``ExecuteLocal`` and ``launch_ros``'s ``Node``
    subclasses ``ExecuteProcess``, so the ``ExecuteLocal`` check catches every
    process-launching action, including ROS nodes.
    """

    def __init__(
        self,
        entities: Iterable[LaunchDescriptionEntity],
        *,
        interval: float,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._interval = interval
        self._staggered = self._build(list(entities))

    def _build(
        self, entities: List[LaunchDescriptionEntity]
    ) -> List[LaunchDescriptionEntity]:
        result: List[LaunchDescriptionEntity] = []
        process_index = 0
        for entity in entities:
            if isinstance(entity, ExecuteLocal):
                if process_index == 0:
                    result.append(entity)  # first process: synchronous, unwrapped
                else:
                    result.append(TimerAction(
                        period=process_index * self._interval, actions=[entity]))
                process_index += 1
            else:
                result.append(entity)  # passthrough, fires immediately
        return result

    def get_sub_entities(self) -> List[LaunchDescriptionEntity]:
        """Return the staggered sub-entities (the launch system iterates these read-only)."""
        return self._staggered

    def execute(self, context: LaunchContext) -> List[LaunchDescriptionEntity]:
        """Return the staggered sub-entities for the launch system to visit."""
        return self._staggered
