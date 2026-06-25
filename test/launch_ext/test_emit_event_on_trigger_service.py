"""Unit tests for EmitEventOnTriggerService.

The trigger callback is driven directly against a real asyncio loop; we inspect
the launch event queue and the response it fills in. The live service call is
covered by test_emit_event_on_trigger_service_integration.py.
"""

import asyncio
from types import SimpleNamespace

from launch import LaunchContext
from launch.event import Event

from launch_ext.actions import EmitEventOnTriggerService


class _Marker(Event):
    name = "test.Marker"


def _drain(loop):
    loop.call_soon(loop.stop)
    loop.run_forever()


def test_on_trigger_emits_the_event_and_returns_success():
    context = LaunchContext()
    loop = asyncio.new_event_loop()
    try:
        context._set_asyncio_loop(loop)
        marker = _Marker()
        action = EmitEventOnTriggerService(
            service_name="/restart", event=marker, success_message="restarting"
        )

        response = SimpleNamespace()
        result = action._on_trigger(SimpleNamespace(), response, context)
        _drain(loop)

        assert result is response
        assert response.success is True
        assert response.message == "restarting"
        assert context._event_queue.get_nowait() is marker
    finally:
        loop.close()


def test_event_factory_is_invoked_per_trigger():
    context = LaunchContext()
    loop = asyncio.new_event_loop()
    try:
        context._set_asyncio_loop(loop)
        action = EmitEventOnTriggerService(service_name="/restart", event=lambda: _Marker())

        action._on_trigger(SimpleNamespace(), SimpleNamespace(), context)
        action._on_trigger(SimpleNamespace(), SimpleNamespace(), context)
        _drain(loop)

        first = context._event_queue.get_nowait()
        second = context._event_queue.get_nowait()
        assert isinstance(first, _Marker)
        assert isinstance(second, _Marker)
        assert first is not second  # a fresh event per call
    finally:
        loop.close()


def test_default_success_message_is_empty():
    context = LaunchContext()
    loop = asyncio.new_event_loop()
    try:
        context._set_asyncio_loop(loop)
        action = EmitEventOnTriggerService(service_name="/restart", event=_Marker())

        response = SimpleNamespace()
        action._on_trigger(SimpleNamespace(), response, context)
        _drain(loop)

        assert response.success is True
        assert response.message == ""
    finally:
        loop.close()
