from launch.actions import ExecuteProcess, LogInfo, TimerAction
from launch.launch_context import LaunchContext

from launch_ext.actions import StaggeredExecute


def _proc(name: str) -> ExecuteProcess:
    return ExecuteProcess(cmd=["echo", name])


def test_three_processes_get_increasing_offsets():
    p0, p1, p2 = _proc("a"), _proc("b"), _proc("c")
    subs = StaggeredExecute([p0, p1, p2], interval=1.0).get_sub_entities()

    # First process is unwrapped (synchronous), rest wrapped in TimerActions.
    assert subs[0] is p0
    assert isinstance(subs[1], TimerAction)
    assert isinstance(subs[2], TimerAction)
    assert subs[1].period == 1.0
    assert subs[2].period == 2.0
    assert list(subs[1].actions) == [p1]
    assert list(subs[2].actions) == [p2]


def test_non_process_entity_passes_through_and_does_not_advance_index():
    p0, p1 = _proc("a"), _proc("b")
    log = LogInfo(msg="hello")
    subs = StaggeredExecute([p0, log, p1], interval=2.0).get_sub_entities()

    assert subs[0] is p0            # first process, unwrapped
    assert subs[1] is log           # passthrough, unchanged
    assert isinstance(subs[2], TimerAction)
    assert subs[2].period == 2.0    # second process still at 1 * interval
    assert list(subs[2].actions) == [p1]


def test_single_process_is_unwrapped():
    p0 = _proc("a")
    subs = StaggeredExecute([p0], interval=5.0).get_sub_entities()
    assert subs == [p0]


def test_empty_list_yields_empty_list():
    assert StaggeredExecute([], interval=1.0).get_sub_entities() == []


def test_no_processes_returns_entities_unchanged():
    log0, log1 = LogInfo(msg="x"), LogInfo(msg="y")
    subs = StaggeredExecute([log0, log1], interval=1.0).get_sub_entities()
    assert subs == [log0, log1]


def test_execute_returns_same_object_as_get_sub_entities():
    action = StaggeredExecute([_proc("a"), _proc("b")], interval=1.0)
    assert action.execute(LaunchContext()) is action.get_sub_entities()
