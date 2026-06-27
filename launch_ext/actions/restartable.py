from typing import Callable, List, Optional, Set

from launch.action import Action
from launch.actions import (
    EmitEvent,
    ExecuteProcess,
    GroupAction,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.events import matches_action
from launch.events.process import ShutdownProcess
from launch.launch_context import LaunchContext
from launch.launch_description_entity import LaunchDescriptionEntity
from launch.some_entities_type import SomeEntitiesType
from launch.utilities import normalize_to_list_of_entities

from ..event_handlers import OnRestart
from ..events import Restart

Factory = Callable[[LaunchContext, Optional[Restart]], SomeEntitiesType]


class Restartable(Action):
    """Wrap a group of entities so they can be torn down and re-created at runtime.

    On execution the action builds its first "generation" of entities from
    ``factory`` and registers an :class:`~launch_ext.event_handlers.OnRestart`
    handler targeting itself. When a :class:`~launch_ext.events.Restart` event
    arrives, the action shuts down the processes from the current generation,
    waits for *all* of them to exit, then asks the factory for a fresh generation
    — passing the triggering ``Restart`` event so the rebuild can be parameterised
    (e.g. with a new ``recording_config_dir``).

    ``factory`` is called as ``factory(context, restart_event)`` and must return
    new entity instances every time (launch actions are single-shot). The first
    call receives ``None``; subsequent calls receive the ``Restart`` event.

    Every generation runs against the *same* :class:`~launch.LaunchContext` (there
    is one per launch run). That context is captured on first execution and reused
    for every restart; :meth:`request_restart` uses it to emit a restart from any
    thread. Because the context is shared, each generation's process registers
    event handlers on it that are not removed when the process dies. By default
    (``prune_event_handlers=True``) those handlers are unregistered when the
    generation is torn down, so they do not accumulate across many restarts.
    """

    def __init__(self, *, factory: Factory, prune_event_handlers: bool = True, **kwargs) -> None:
        """Create a Restartable driven by ``factory``."""
        super().__init__(**kwargs)
        self._factory = factory
        self._prune_event_handlers = prune_event_handlers
        self._context: Optional[LaunchContext] = None
        self._processes: List[ExecuteProcess] = []
        self._pending_restart: Optional[Restart] = None
        self._pending_exits = 0
        # Handler bookkeeping for pruning.
        self._handlers_before_generation_ids: Set[int] = set()
        self._generation_handlers: List = []
        self._teardown_baseline_ids: Set[int] = set()

    @property
    def context(self) -> Optional[LaunchContext]:
        """The launch context captured on first execution (``None`` until executed)."""
        return self._context

    def execute(self, context: LaunchContext) -> Optional[List[LaunchDescriptionEntity]]:
        """Register the restart handler and return the first generation of entities."""
        self._context = context
        context.register_event_handler(OnRestart(target_action=self, on_restart=self._on_restart))
        return self._spawn(context, None)

    def request_restart(self, **payload) -> None:
        """Request a restart from any thread, using the captured launch context.

        Emits a :class:`~launch_ext.events.Restart` targeting this action with the
        given payload, scheduled onto the launch event loop so it is safe to call
        from a ROS callback or other background thread.
        """
        if self._context is None:
            raise RuntimeError(
                "Restartable.request_restart() called before the action was executed"
            )
        event = Restart(action=self, **payload)
        self._context.asyncio_loop.call_soon_threadsafe(self._context.emit_event_sync, event)

    def _spawn(
        self, context: LaunchContext, restart_event: Optional[Restart]
    ) -> List[LaunchDescriptionEntity]:
        entities = normalize_to_list_of_entities(self._factory(context, restart_event))
        self._processes = self._collect_processes(entities)
        if self._prune_event_handlers:
            # Snapshot the handlers present before this generation registers any,
            # and append a marker that records what the generation added (so it can
            # be unregistered on teardown). The marker runs after the generation's
            # entities, within the same visitation, so it sees their handlers.
            self._handlers_before_generation_ids = {id(h) for h in context._event_handlers}
            entities = [*entities, _CaptureGenerationHandlers(self)]
        return entities

    def _on_restart(
        self, event: Restart, context: LaunchContext
    ) -> Optional[List[LaunchDescriptionEntity]]:
        # A restart that arrives mid-teardown just updates the target: the
        # in-flight teardown will recreate with this latest payload. We must not
        # emit a second round of shutdowns for processes already being killed.
        if self._pending_exits > 0:
            self._pending_restart = event
            return None

        self._pending_restart = event

        # Nothing running (e.g. the generation was config-only) — recreate now.
        if not self._processes:
            self._prune_generation(context)
            return self._spawn(context, event)

        # Snapshot the handlers present now so that any added *during* teardown
        # (e.g. ExecuteProcess's sigterm/sigkill timer OnShutdown handlers) can
        # also be pruned, not just the ones added when the generation started.
        self._teardown_baseline_ids = {id(h) for h in context._event_handlers}
        self._pending_exits = len(self._processes)
        entities: List[LaunchDescriptionEntity] = []
        for proc in self._processes:
            entities.append(
                RegisterEventHandler(
                    OnProcessExit(
                        target_action=proc,
                        on_exit=self._on_child_exit,
                        handle_once=True,
                    )
                )
            )
            entities.append(EmitEvent(event=ShutdownProcess(process_matcher=matches_action(proc))))
        return entities

    def _on_child_exit(
        self, event, context: LaunchContext
    ) -> Optional[List[LaunchDescriptionEntity]]:
        self._pending_exits -= 1
        if self._pending_exits > 0:
            return None  # still waiting for the rest of the generation to die
        # The generation is fully dead: drop the event handlers it left behind
        # before building the next one.
        self._prune_generation(context)
        restart_event = self._pending_restart
        self._pending_restart = None
        return self._spawn(context, restart_event)

    def _prune_generation(self, context: LaunchContext) -> None:
        """Unregister event handlers the just-finished generation left behind.

        This covers both the handlers its processes registered on startup
        (captured by the spawn marker) and any registered while it was being torn
        down (diffed against the teardown baseline). Handlers that existed before
        the generation — the restart handler, sibling actions — are untouched.
        """
        if not self._prune_event_handlers:
            return
        to_remove = list(self._generation_handlers)
        if self._teardown_baseline_ids:
            to_remove += [
                h for h in context._event_handlers if id(h) not in self._teardown_baseline_ids
            ]
        for handler in to_remove:
            try:
                context.unregister_event_handler(handler)
            except ValueError:
                pass  # already gone (e.g. a handle_once handler that fired)
        self._generation_handlers = []
        self._teardown_baseline_ids = set()

    @staticmethod
    def _collect_processes(entities) -> List[ExecuteProcess]:
        """Recursively collect ExecuteProcess instances from a list of entities."""
        processes: List[ExecuteProcess] = []
        for entity in entities:
            if isinstance(entity, ExecuteProcess):
                processes.append(entity)
            elif isinstance(entity, GroupAction):
                processes.extend(Restartable._collect_processes(entity.get_sub_entities()))
            elif isinstance(entity, (list, tuple)):
                processes.extend(Restartable._collect_processes(entity))
        return processes


class _CaptureGenerationHandlers(Action):
    """Internal marker: records the event handlers a Restartable generation added.

    Visited last within a generation, it diffs the context's handler list against
    the snapshot taken when the generation was spawned, storing the difference on
    the owning Restartable so they can be pruned when the generation is torn down.
    """

    def __init__(self, owner: Restartable) -> None:
        super().__init__()
        self._owner = owner

    def execute(self, context: LaunchContext) -> None:
        before = self._owner._handlers_before_generation_ids
        self._owner._generation_handlers = [
            h for h in context._event_handlers if id(h) not in before
        ]
        return None
