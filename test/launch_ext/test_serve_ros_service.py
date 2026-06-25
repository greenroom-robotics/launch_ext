"""Unit tests for the generic ServeROSService action.

The shared launch_ros node is faked via monkeypatch so the create_service wiring
and request dispatch can be checked without a running ROS graph. The live path is
covered by test_emit_event_on_trigger_service.py.
"""

from types import SimpleNamespace

import launch_ros.ros_adapters as ros_adapters

from launch import LaunchContext

from launch_ext.actions import ServeROSService


class _FakeNode:
    def __init__(self):
        self.created = None
        self.callback = None

    def create_service(self, srv_type, service_name, callback):
        self.created = (srv_type, service_name)
        self.callback = callback
        return f"service:{service_name}"


def test_stores_service_parameters():
    action = ServeROSService(srv_type=int, service_name="/restart", callback=lambda q, r, c: r)

    assert action._srv_type is int
    assert action._service_name == "/restart"


def test_execute_creates_the_service_on_the_shared_node(monkeypatch):
    node = _FakeNode()
    monkeypatch.setattr(ros_adapters, "get_ros_node", lambda context: node)

    action = ServeROSService(srv_type=int, service_name="/restart", callback=lambda q, r, c: r)
    action.execute(LaunchContext())

    assert node.created == (int, "/restart")
    assert action._service == "service:/restart"


def test_request_is_dispatched_to_callback_with_context(monkeypatch):
    node = _FakeNode()
    monkeypatch.setattr(ros_adapters, "get_ros_node", lambda context: node)

    seen = {}

    def callback(request, response, context):
        seen["request"] = request
        seen["context"] = context
        response.handled = True
        return response

    context = LaunchContext()
    action = ServeROSService(srv_type=int, service_name="/restart", callback=callback)
    action.execute(context)

    response = SimpleNamespace()
    # Simulate rclpy invoking the registered (request, response) callback.
    result = node.callback("the-request", response)

    assert result is response
    assert response.handled is True
    assert seen["request"] == "the-request"
    assert seen["context"] is context
