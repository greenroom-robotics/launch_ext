"""Tests for the configure_middleware function."""

import pytest

from launch import LaunchContext
from launch.actions import ExecuteProcess, RegisterEventHandler, SetLaunchConfiguration
from launch.utilities import perform_substitutions

from launch_ext.actions import ConfigureZenoh
from launch_ext.discovery.configure_middleware import configure_middleware
from launch_ext.discovery.middleware_config import MiddlewareConfig, ZenohMiddleware, FastDDSMiddleware, MiddlewareTypes, FastDDSDiscoveryType


def _name_of(set_launch_configuration: SetLaunchConfiguration) -> str:
    return perform_substitutions(LaunchContext(), set_launch_configuration.name)


def test_zenoh_returns_reset_and_configure_zenoh():
    result = configure_middleware(MiddlewareConfig(middleware=MiddlewareTypes.ZENOH))

    assert isinstance(result, list)
    assert len(result) == 2
    # The fastdds super client config is reset...
    assert isinstance(result[0], SetLaunchConfiguration)
    assert _name_of(result[0]) == "fastdds_profile_super_client"
    # ...and zenoh is configured.
    assert isinstance(result[1], ConfigureZenoh)


def test_zenoh_appends_then():
    then = SetLaunchConfiguration("my_flag", "1")
    result = configure_middleware(MiddlewareConfig(middleware=MiddlewareTypes.ZENOH), then=then)

    assert len(result) == 3
    # `then` entities are appended after the zenoh setup.
    assert result[-1] is then


def test_zenoh_run_router_peers_is_valid():
    # router_peers triggers a deep_merge into the router config; the returned
    # structure should be unchanged and not raise.
    result = configure_middleware(
        MiddlewareConfig(
            middleware=MiddlewareTypes.ZENOH,
            zenoh=ZenohMiddleware(router_peers=["10.0.0.1", "10.0.0.2"], run_router=True),
        )
    )

    assert [type(entity) for entity in result] == [SetLaunchConfiguration, ConfigureZenoh]


def test_fastdds_discovery_server_without_running_server():
    result = configure_middleware(
        MiddlewareConfig(middleware=MiddlewareTypes.FASTDDS, fastdds=FastDDSMiddleware(discovery_type=FastDDSDiscoveryType.DISCOVERY_SERVER)),
        run_server=False,
    )

    # ExecuteAndAfterProcessExit returns [process, RegisterEventHandler]; here the
    # outer process stops the ros2 daemon before the rest of the setup runs.
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], ExecuteProcess)
    assert isinstance(result[1], RegisterEventHandler)


def test_fastdds_simple_not_implemented():
    with pytest.raises(NotImplementedError):
        configure_middleware(
            MiddlewareConfig(middleware=MiddlewareTypes.FASTDDS, fastdds=FastDDSMiddleware(discovery_type=FastDDSDiscoveryType.SIMPLE))
        )


def test_fastdds_easy_not_implemented():
    with pytest.raises(NotImplementedError):
        configure_middleware(
            MiddlewareConfig(middleware=MiddlewareTypes.FASTDDS, fastdds=FastDDSMiddleware(discovery_type=FastDDSDiscoveryType.EASY))
        )


def test_fastdds_discovery_server_with_running_server():
    result = configure_middleware(
        MiddlewareConfig(middleware=MiddlewareTypes.FASTDDS, fastdds=FastDDSMiddleware(discovery_type=FastDDSDiscoveryType.DISCOVERY_SERVER)),
        run_server=True,
    )

    # Same nested ExecuteAndAfterProcessExit shape as the no-server case; the
    # discovery server is wired in via the inner on-exit actions.
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], ExecuteProcess)
    assert isinstance(result[1], RegisterEventHandler)
