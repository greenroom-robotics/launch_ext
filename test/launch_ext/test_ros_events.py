"""Unit tests for the ROS-bridging events and their handlers.

These are pure-Python: no rclpy, no running launch loop. They pin down the event
payloads and the matching/dispatch behaviour of the handlers.
"""

from types import SimpleNamespace

from launch import LaunchContext
from launch.actions import ExecuteProcess
from launch.event import Event

from launch_ext.events import ROSMessageReceived, Restart
from launch_ext.event_handlers import OnROSMessage, OnRestart

# --- ROSMessageReceived -----------------------------------------------------


def test_ros_message_received_carries_topic_and_msg():
    msg = SimpleNamespace(data="hello")
    event = ROSMessageReceived(topic="/playback_state", msg=msg)

    assert event.topic == "/playback_state"
    assert event.msg is msg
    assert event.name == "launch_ext.events.ROSMessageReceived"
    assert isinstance(event, Event)


# --- OnROSMessage -----------------------------------------------------------


def test_on_ros_message_matches_only_its_topic():
    handler = OnROSMessage(topic="/playback_state", on_message=lambda e, c: None)

    assert handler.matches(ROSMessageReceived(topic="/playback_state", msg=None)) is True
    assert handler.matches(ROSMessageReceived(topic="/other", msg=None)) is False


def test_on_ros_message_ignores_unrelated_events():
    handler = OnROSMessage(topic="/playback_state", on_message=lambda e, c: None)

    assert handler.matches(Event()) is False


def test_on_ros_message_passes_event_to_callback_and_returns_entities():
    seen = []
    deferred = ExecuteProcess(cmd=["true"])

    def on_message(event, context):
        seen.append(event)
        return [deferred]

    handler = OnROSMessage(topic="/playback_state", on_message=on_message)
    event = ROSMessageReceived(topic="/playback_state", msg="payload")

    result = handler.handle(event, LaunchContext())

    assert seen == [event]
    assert result == [deferred]


# --- Restart ----------------------------------------------------------------


def test_restart_carries_target_action_and_payload():
    action = ExecuteProcess(cmd=["true"])
    event = Restart(action=action, recording_config_dir="/recordings/abc")

    assert event.action is action
    assert event.payload == {"recording_config_dir": "/recordings/abc"}
    assert event.name == "launch_ext.events.Restart"


def test_restart_payload_defaults_to_empty():
    action = ExecuteProcess(cmd=["true"])
    event = Restart(action=action)

    assert event.payload == {}


# --- OnRestart --------------------------------------------------------------


def test_on_restart_matches_only_its_target_action():
    target = ExecuteProcess(cmd=["true"])
    other = ExecuteProcess(cmd=["true"])
    handler = OnRestart(target_action=target, on_restart=lambda e, c: None)

    assert handler.matches(Restart(action=target)) is True
    assert handler.matches(Restart(action=other)) is False


def test_on_restart_without_target_matches_any_restart():
    handler = OnRestart(on_restart=lambda e, c: None)

    assert handler.matches(Restart(action=ExecuteProcess(cmd=["true"]))) is True


def test_on_restart_does_not_match_other_events():
    handler = OnRestart(on_restart=lambda e, c: None)

    assert handler.matches(ROSMessageReceived(topic="/x", msg=None)) is False


def test_on_restart_invokes_callback_with_event():
    target = ExecuteProcess(cmd=["true"])
    seen = []
    handler = OnRestart(target_action=target, on_restart=lambda e, c: seen.append(e) or [])
    event = Restart(action=target, gen=2)

    handler.handle(event, LaunchContext())

    assert seen == [event]
    assert seen[0].payload == {"gen": 2}
