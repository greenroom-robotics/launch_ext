"""End-to-end test for SubscribeRosTopic.

Runs a real LaunchService that subscribes to a topic via the shared launch_ros
node, publishes to it from a separate rclpy node, and asserts the message is
delivered to an OnROSMessage handler. The LaunchService runs on the main thread;
a watchdog thread guarantees termination if delivery never happens.
"""

import threading
import time

import rclpy
from rclpy.qos import (
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
    QoSProfile,
    QoSReliabilityPolicy,
)
from std_msgs.msg import String

from launch import LaunchDescription, LaunchService
from launch.actions import RegisterEventHandler, TimerAction

from launch_ext.actions import SubscribeRosTopic
from launch_ext.event_handlers import OnROSMessage

TOPIC = "/launch_ext_itest"

QOS = QoSProfile(
    depth=1,
    durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
    history=QoSHistoryPolicy.KEEP_LAST,
    reliability=QoSReliabilityPolicy.RELIABLE,
)


def _publish_until(stop: threading.Event):
    rclpy.init()
    node = rclpy.create_node("launch_ext_itest_publisher")
    pub = node.create_publisher(String, TOPIC, QOS)
    try:
        while not stop.is_set():
            pub.publish(String(data="hello"))
            time.sleep(0.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()


def test_subscribe_ros_topic_delivers_message_to_handler():
    received = []
    got_message = threading.Event()

    def on_message(event, context):
        received.append(event.msg.data)
        got_message.set()
        return None

    ld = LaunchDescription(
        [
            SubscribeRosTopic(msg_type=String, topic=TOPIC, qos=QOS),
            RegisterEventHandler(OnROSMessage(topic=TOPIC, on_message=on_message)),
            # Keepalive: without a pending future the service would shut down as
            # "idle" at startup, before the first message is delivered.
            TimerAction(period=60.0, actions=[]),
        ]
    )

    ls = LaunchService()
    ls.include_launch_description(ld)

    stop = threading.Event()
    pub_thread = threading.Thread(target=_publish_until, args=(stop,), daemon=True)

    def shutdown_when_received():
        got_message.wait(timeout=25)
        ls.shutdown()  # proper shutdown path (sets shutting-down flag, fires once)

    shutter = threading.Thread(target=shutdown_when_received, daemon=True)
    pub_thread.start()
    shutter.start()

    ls.run()

    stop.set()
    pub_thread.join(timeout=5)

    assert received, "OnROSMessage handler never fired (message not delivered)"
    assert received[0] == "hello"
