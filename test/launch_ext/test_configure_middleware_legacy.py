"""Tests for the restored pre-2.0 middleware interface."""

from launch.actions import ExecuteProcess, RegisterEventHandler, SetLaunchConfiguration
from launch.event_handlers import OnProcessExit

from launch_ext.actions import ConfigureFastDDS, ConfigureFastDDSEasyMode, ConfigureZenoh
from launch_ext.discovery import configure_middleware
from launch_ext.discovery.discovery_config import Discovery
from launch_ext.substitutions import (
    FastDDSClientEnvironment,
    FastDDSClientPath,
    FastDDSSuperclientEnvironment,
    get_fastdds_superclient_environment,
)


def test_zenoh_returns_super_client_reset_and_configure_zenoh():
    result = configure_middleware(Discovery(type="zenoh"))

    assert len(result) == 2
    assert isinstance(result[0], SetLaunchConfiguration)
    assert isinstance(result[1], ConfigureZenoh)


def test_zenoh_appends_then():
    then = SetLaunchConfiguration("my_flag", "1")
    result = configure_middleware(Discovery(type="zenoh"), then=then)

    assert len(result) == 3
    assert result[2] is then


def test_easy_returns_easy_mode_action():
    result = configure_middleware(Discovery(type="easy"))

    assert len(result) == 1
    assert isinstance(result[0], ConfigureFastDDSEasyMode)


def test_simple_returns_configure_fastdds():
    result = configure_middleware(Discovery(type="simple"))

    assert len(result) == 1
    assert isinstance(result[0], ConfigureFastDDS)


def test_fastdds_wraps_daemon_stop_and_shm_clean():
    result = configure_middleware(Discovery(type="fastdds"))

    # ExecuteAndAfterProcessExit is a function returning [process, RegisterEventHandler],
    # so the fastdds branch yields the daemon-stop process and its on-exit handler.
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], ExecuteProcess)
    assert isinstance(result[1], RegisterEventHandler)
    assert isinstance(result[1].event_handler, OnProcessExit)


def test_superclient_environment_sets_the_profile_env_var():
    env = get_fastdds_superclient_environment("fastdds")

    assert len(env) == 1
    value = next(iter(env.values()))
    assert isinstance(value, FastDDSSuperclientEnvironment)


def test_superclient_environment_is_empty_in_easy_mode():
    assert get_fastdds_superclient_environment("easy") == {}


def test_client_environment_alias_is_the_client_path_class():
    assert FastDDSClientEnvironment is FastDDSClientPath
