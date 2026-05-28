from types import SimpleNamespace

from launch import LaunchContext
from launch.actions import ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessIO

from launch_ext.actions import RunAfterProcessOutput


def _io(text: bytes) -> SimpleNamespace:
    """A minimal stand-in for ProcessIO — only the ``text`` attribute is read."""
    return SimpleNamespace(text=text)


def _make_action(match: bytes, then: list) -> RunAfterProcessOutput:
    target = ExecuteProcess(cmd=["true"])
    return RunAfterProcessOutput(target=target, match=match, then=then)


def test_match_returns_then_actions():
    then = [ExecuteProcess(cmd=["echo", "deferred"])]
    action = _make_action(b"Running on:", then)

    result = action._on_stdout(_io(b"   Running on: 127.0.0.1\n"))

    assert result == then


def test_non_matching_line_returns_none():
    then = [ExecuteProcess(cmd=["echo", "deferred"])]
    action = _make_action(b"Running on:", then)

    assert action._on_stdout(_io(b"some other log line\n")) is None
    assert action._fired is False


def test_fires_only_once():
    then = [ExecuteProcess(cmd=["echo", "deferred"])]
    action = _make_action(b"Running on:", then)

    first = action._on_stdout(_io(b"Running on: 127.0.0.1\n"))
    second = action._on_stdout(_io(b"Running on: 127.0.0.1 (again)\n"))

    assert first == then
    assert second is None
    assert action._fired is True


def test_match_can_be_substring_of_longer_line():
    then = [ExecuteProcess(cmd=["echo"])]
    action = _make_action(b"Running on:", then)

    result = action._on_stdout(_io(b"[discovery_server] INFO    Running on: 0.0.0.0:11811\n"))

    assert result == then


def test_empty_then_still_fires():
    action = _make_action(b"Running on:", [])

    result = action._on_stdout(_io(b"Running on: x\n"))

    assert result == []
    assert action._fired is True


def test_execute_registers_on_process_io_handler():
    target = ExecuteProcess(cmd=["true"])
    then = [ExecuteProcess(cmd=["echo"])]
    action = RunAfterProcessOutput(target=target, match=b"ready", then=then)

    entities = action.execute(LaunchContext())

    assert len(entities) == 1
    reh = entities[0]
    assert isinstance(reh, RegisterEventHandler)
    assert isinstance(reh.event_handler, OnProcessIO)
