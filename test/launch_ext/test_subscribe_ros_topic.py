"""Unit tests for the SubscribeRosTopic bridge action.

These cover the message->launch-event hop without rclpy: we drive the internal
callback directly against a real asyncio loop and inspect the launch event queue.
The full get_ros_node + subscription path is covered by the integration test.
"""

import asyncio

from launch import LaunchContext
from launch.event import Event

from launch_ext.actions import SubscribeRosTopic
from launch_ext.events import ROSMessageReceived


class _CustomEvent(Event):
    name = "test.CustomEvent"

    def __init__(self, *, topic, msg):
        self.topic = topic
        self.msg = msg


def _drain(loop):
    """Run the loop just long enough to execute pending threadsafe callbacks."""
    loop.call_soon(loop.stop)
    loop.run_forever()


def test_stores_subscription_parameters():
    action = SubscribeRosTopic(msg_type=int, topic="/playback_state", qos=5)

    assert action._msg_type is int
    assert action._topic == "/playback_state"
    assert action._qos == 5


def test_handle_message_emits_ros_message_received_on_the_launch_loop():
    context = LaunchContext()
    loop = asyncio.new_event_loop()
    try:
        context._set_asyncio_loop(loop)
        action = SubscribeRosTopic(msg_type=object, topic="/playback_state", qos=1)

        action._handle_message(context, "the-message")
        _drain(loop)

        event = context._event_queue.get_nowait()
        assert isinstance(event, ROSMessageReceived)
        assert event.topic == "/playback_state"
        assert event.msg == "the-message"
    finally:
        loop.close()


def test_handle_message_honours_a_custom_event_factory():
    context = LaunchContext()
    loop = asyncio.new_event_loop()
    try:
        context._set_asyncio_loop(loop)
        action = SubscribeRosTopic(
            msg_type=object,
            topic="/t",
            qos=1,
            event_factory=lambda topic, msg: _CustomEvent(topic=topic, msg=msg),
        )

        action._handle_message(context, "m")
        _drain(loop)

        event = context._event_queue.get_nowait()
        assert isinstance(event, _CustomEvent)
        assert event.topic == "/t"
        assert event.msg == "m"
    finally:
        loop.close()
