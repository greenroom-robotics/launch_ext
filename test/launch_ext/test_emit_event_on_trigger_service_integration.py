"""End-to-end test for EmitEventOnTriggerService.

Runs a real LaunchService that offers a Trigger service (on the shared launch_ros
node), calls it from a separate rclpy client, and asserts that the configured
event is emitted to a launch event handler and that the service returns success.
The LaunchService runs on the main thread; a watchdog guarantees termination.
"""

import threading
import time

import rclpy
from std_srvs.srv import Trigger

from launch import LaunchDescription, LaunchService
from launch.actions import OpaqueFunction, RegisterEventHandler, TimerAction
from launch.event import Event
from launch.event_handler import EventHandler

from launch_ext.actions import EmitEventOnTriggerService

SERVICE = "/launch_ext_trigger_itest"


class _RestartMarker(Event):
    name = "test.RestartMarker"


def _call_trigger(call_done: threading.Event, result: dict):
    rclpy.init()
    node = rclpy.create_node("launch_ext_trigger_client")
    client = node.create_client(Trigger, SERVICE)
    try:
        if not client.wait_for_service(timeout_sec=15):
            result["error"] = "service never appeared"
            return
        future = client.call_async(Trigger.Request())
        deadline = time.time() + 10
        while not future.done() and time.time() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
        if future.done():
            result["success"] = future.result().success
    finally:
        call_done.set()
        node.destroy_node()
        rclpy.shutdown()


def test_trigger_service_call_emits_event_to_handler():
    event_received = threading.Event()

    def on_marker(context):
        event_received.set()
        return None

    ld = LaunchDescription(
        [
            EmitEventOnTriggerService(service_name=SERVICE, event=_RestartMarker()),
            RegisterEventHandler(
                EventHandler(
                    matcher=lambda e: isinstance(e, _RestartMarker),
                    entities=[OpaqueFunction(function=on_marker)],
                )
            ),
            # Keepalive so the service is offered and stays up until we call it.
            TimerAction(period=60.0, actions=[]),
        ]
    )

    ls = LaunchService()
    ls.include_launch_description(ld)

    call_done = threading.Event()
    result = {}

    threading.Thread(target=_call_trigger, args=(call_done, result), daemon=True).start()

    def shutdown_when_done():
        # Wait until both the event fired and the client got its response, so the
        # service isn't torn down mid-call.
        event_received.wait(timeout=25)
        call_done.wait(timeout=10)
        ls.shutdown()

    threading.Thread(target=shutdown_when_done, daemon=True).start()

    ls.run()

    assert "error" not in result, result.get("error")
    assert event_received.is_set(), "the Trigger call did not emit the event to the handler"
    assert result.get("success") is True
