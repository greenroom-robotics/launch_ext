"""Unit tests for Restartable bookkeeping.

No launch loop runs here: we drive the action's lifecycle methods directly and
assert on the entities/handlers it produces. The live end-to-end behaviour is
covered in test_restartable_action_integration.py.
"""

import asyncio

import pytest

from launch import LaunchContext
from launch.actions import (
    EmitEvent,
    ExecuteProcess,
    GroupAction,
    RegisterEventHandler,
    SetLaunchConfiguration,
)
from launch.event_handler import EventHandler
from launch.event_handlers import OnProcessExit
from launch.events.process import ShutdownProcess

from launch_ext.actions import Restartable
from launch_ext.actions.restartable import _CaptureGenerationHandlers
from launch_ext.event_handlers import OnRestart
from launch_ext.events import Restart


def _proc(tag: str) -> ExecuteProcess:
    return ExecuteProcess(cmd=["echo", tag])


def _gen_factory(record: list):
    """Factory that records each call and returns one process tagged by generation."""

    def factory(context, restart_event):
        gen = restart_event.payload["gen"] if restart_event is not None else 0
        proc = _proc(f"gen-{gen}")
        record.append((gen, proc))
        return [proc]

    return factory


# --- execute / first generation ---------------------------------------------


def test_execute_returns_first_generation_from_factory_with_no_event():
    record = []
    action = Restartable(factory=_gen_factory(record))

    entities = action.execute(LaunchContext())

    assert len(record) == 1
    gen, proc = record[0]
    assert gen == 0
    # factory output, followed by the internal handler-capture marker
    assert entities[0] is proc
    assert isinstance(entities[-1], _CaptureGenerationHandlers)


def test_execute_registers_an_on_restart_handler_targeting_itself():
    context = LaunchContext()
    action = Restartable(factory=_gen_factory([]))
    other = Restartable(factory=_gen_factory([]))

    action.execute(context)

    handlers = [h for h in context._event_handlers if h.matches(Restart(action=action))]
    assert len(handlers) == 1
    # the handler must not fire for a different restartable action
    assert not handlers[0].matches(Restart(action=other))


def test_execute_tracks_the_spawned_processes():
    action = Restartable(factory=_gen_factory([]))
    action.execute(LaunchContext())

    assert len(action._processes) == 1
    assert isinstance(action._processes[0], ExecuteProcess)


# --- restart: teardown of the current generation ----------------------------


def test_restart_emits_shutdown_and_registers_exit_handler_per_process():
    context = LaunchContext()
    record = []
    action = Restartable(factory=_gen_factory(record))
    action.execute(context)
    proc0 = action._processes[0]

    entities = action._on_restart(Restart(action=action, gen=1), context)

    # one RegisterEventHandler(OnProcessExit) + one EmitEvent(ShutdownProcess) per process
    rehs = [e for e in entities if isinstance(e, RegisterEventHandler)]
    emits = [e for e in entities if isinstance(e, EmitEvent)]
    assert len(rehs) == 1
    assert len(emits) == 1
    assert isinstance(rehs[0].event_handler, OnProcessExit)
    assert isinstance(emits[0].event, ShutdownProcess)
    # the shutdown must target exactly the currently-running process
    assert emits[0].event.process_matcher(proc0) is True
    assert emits[0].event.process_matcher(_proc("unrelated")) is False
    # the factory has NOT been called again yet (no recreate until the old gen dies)
    assert len(record) == 1


def test_restart_with_no_running_processes_respawns_immediately():
    context = LaunchContext()
    record = []

    def factory(context, restart_event):
        gen = restart_event.payload["gen"] if restart_event is not None else 0
        record.append(gen)
        return [SetLaunchConfiguration("x", "y")]  # no processes

    action = Restartable(factory=factory)
    action.execute(context)
    assert action._processes == []

    entities = action._on_restart(Restart(action=action, gen=7), context)

    assert record == [0, 7]  # spawned again right away
    non_markers = [e for e in entities if not isinstance(e, _CaptureGenerationHandlers)]
    assert all(isinstance(e, SetLaunchConfiguration) for e in non_markers)


# --- restart: recreate only after the whole generation has exited -----------


def test_recreate_waits_for_all_processes_to_exit():
    context = LaunchContext()
    record = []
    action = Restartable(factory=_multi_factory(record, count=2))
    action.execute(context)
    assert len(action._processes) == 2

    action._on_restart(Restart(action=action, gen=1), context)

    # first child exits -> still waiting, no new generation
    assert action._on_child_exit(None, context) is None
    assert len(record) == 1  # factory not called again yet

    # last child exits -> recreate with the pending restart payload
    new_entities = action._on_child_exit(None, context)
    assert len(record) == 2
    assert record[1]["gen"] == 1
    assert new_entities[:-1] == record[1]["procs"]  # trailing entity is the capture marker
    assert isinstance(new_entities[-1], _CaptureGenerationHandlers)


def test_recreate_uses_fresh_process_instances():
    context = LaunchContext()
    record = []
    action = Restartable(factory=_gen_factory(record))
    action.execute(context)
    first = action._processes[0]

    action._on_restart(Restart(action=action, gen=1), context)
    action._on_child_exit(None, context)
    second = action._processes[0]

    assert first is not second  # single-shot guard => must be a new instance


def test_restart_during_restart_keeps_latest_payload_without_double_teardown():
    context = LaunchContext()
    record = []
    action = Restartable(factory=_gen_factory(record))
    action.execute(context)

    action._on_restart(Restart(action=action, gen=1), context)
    # a second restart arrives before the first finished tearing down
    second = action._on_restart(Restart(action=action, gen=2), context)

    assert second is None  # no second teardown emitted
    assert action._pending_exits == 1  # still only one outstanding exit

    action._on_child_exit(None, context)
    # recreated with the *latest* payload
    assert record[-1][0] == 2


# --- process collection helper ----------------------------------------------


def test_collect_processes_finds_processes_in_a_mixed_list():
    p0, p1 = _proc("a"), _proc("b")
    entities = [SetLaunchConfiguration("k", "v"), p0, p1]

    assert Restartable._collect_processes(entities) == [p0, p1]


def test_collect_processes_descends_into_group_actions():
    p0, p1 = _proc("a"), _proc("b")
    entities = [p0, GroupAction([p1])]

    assert Restartable._collect_processes(entities) == [p0, p1]


# --- captured context / request_restart -------------------------------------


def test_execute_captures_the_launch_context():
    context = LaunchContext()
    action = Restartable(factory=_gen_factory([]))

    assert action.context is None
    action.execute(context)
    assert action.context is context


def test_request_restart_before_execute_raises():
    action = Restartable(factory=_gen_factory([]))

    with pytest.raises(RuntimeError):
        action.request_restart(gen=1)


def test_request_restart_emits_a_restart_event_on_the_loop():
    context = LaunchContext()
    loop = asyncio.new_event_loop()
    try:
        context._set_asyncio_loop(loop)
        action = Restartable(factory=_gen_factory([]))
        action.execute(context)

        action.request_restart(recording_config_dir="/recordings/x")
        loop.call_soon(loop.stop)
        loop.run_forever()

        event = context._event_queue.get_nowait()
        assert isinstance(event, Restart)
        assert event.action is action
        assert event.payload == {"recording_config_dir": "/recordings/x"}
    finally:
        loop.close()


# --- event-handler pruning --------------------------------------------------


def test_spawn_appends_a_capture_marker_when_pruning_enabled():
    action = Restartable(factory=_gen_factory([]))
    entities = action.execute(LaunchContext())

    assert isinstance(entities[-1], _CaptureGenerationHandlers)


def test_generation_handlers_are_pruned_on_restart():
    context = LaunchContext()
    action = Restartable(factory=_gen_factory([]))
    entities = action.execute(context)
    marker = entities[-1]

    on_restart_handlers = [h for h in context._event_handlers if isinstance(h, OnRestart)]
    assert len(on_restart_handlers) == 1

    # Simulate a process registering a handler during this generation's visitation.
    leaked = EventHandler(matcher=lambda event: False)
    context.register_event_handler(leaked)
    marker.execute(context)  # records the generation's handlers (incl. leaked)
    assert leaked in list(context._event_handlers)

    # Restart: tear down then recreate.
    action._on_restart(Restart(action=action, gen=1), context)
    action._on_child_exit(None, context)

    assert leaked not in list(context._event_handlers)  # pruned
    # the restart handler itself is preserved
    assert [h for h in context._event_handlers if isinstance(h, OnRestart)] == on_restart_handlers


def test_pruning_can_be_disabled():
    context = LaunchContext()
    action = Restartable(factory=_gen_factory([]), prune_event_handlers=False)
    entities = action.execute(context)

    assert not any(isinstance(e, _CaptureGenerationHandlers) for e in entities)

    leaked = EventHandler(matcher=lambda event: False)
    context.register_event_handler(leaked)

    action._on_restart(Restart(action=action, gen=1), context)
    action._on_child_exit(None, context)

    assert leaked in list(context._event_handlers)  # left in place


def _multi_factory(record: list, count: int):
    def factory(context, restart_event):
        gen = restart_event.payload["gen"] if restart_event is not None else 0
        procs = [_proc(f"gen-{gen}-{i}") for i in range(count)]
        record.append({"gen": gen, "procs": procs})
        return procs

    return factory
