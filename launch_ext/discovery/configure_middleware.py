from launch.actions import SetLaunchConfiguration, ExecuteProcess
from launch.launch_description_entity import LaunchDescriptionEntity

from launch_ext.actions.configure_zenoh import deep_merge
from launch_ext.discovery.discovery_config import Discovery

from launch_ext.actions.configure_fastdds import ConfigureFastDDS
from launch_ext.actions.configure_fastdds_easy import ConfigureFastDDSEasyMode
from launch_ext.actions.configure_zenoh import ConfigureZenoh
from launch_ext.actions.execute_after_process_output import ExecuteAfterProcessOutput
from launch_ext.actions.execute_and_after_process_exit import ExecuteAndAfterProcessExit


def configure_middleware(
    discovery: Discovery,
    with_server=True,
    then: list[LaunchDescriptionEntity] | None = None,
):
    then = list(then) if then else []

    if discovery.type == "zenoh":
        zenoh = discovery.zenoh
        router_peers = zenoh.router_peers
        router_config = zenoh.router_config
        session_config = zenoh.session_config

        # Merge router_peers into router_config connect/endpoints
        if router_peers:
            peer_endpoints = [f"tcp/{peer}:7447" for peer in router_peers]
            router_config = deep_merge(
                router_config,
                {"connect": {"endpoints": peer_endpoints}},
            )

        return [
            SetLaunchConfiguration("fastdds_profile_super_client", ""),
            ConfigureZenoh(
                with_router=zenoh.with_router and with_server,
                router_config=router_config,
                session_config=session_config,
                generate_router_config_file=True,
                generate_session_config_file=True,
            ),
            *then,
        ]

    if discovery.type == "fastdds":
        fastdds = discovery.fastdds

        cfg = ConfigureFastDDS(
            with_discovery_server=fastdds.with_discovery_server and with_server,
            discovery_server_ip=fastdds.discovery_server_ip,
            allowed_interfaces=fastdds.allowed_interfaces,
            simple_discovery=False,
        )

        stop_ros2_daemon = ExecuteProcess(
            name="stop_ros2_daemon",
            cmd=[
                "ros2",
                "daemon",
                "stop",
            ],
            output={"both": ["log", "screen"]},
        )

        shm_clean = ExecuteProcess(
            name="shm_clean",
            cmd=[
                "fastdds",
                "shm",
                "clean",
            ],
            output={"both": ["log", "screen"]},
        )

        after_actions = then

        if cfg.discovery_server:
            after_actions = [
                ExecuteAfterProcessOutput(
                    target=cfg.discovery_server,
                    match=b"Running on:",
                    then=then,
                ),
                cfg,
            ]
        else:
            after_actions = [cfg] + after_actions

        return ExecuteAndAfterProcessExit(
            stop_ros2_daemon, ExecuteAndAfterProcessExit(shm_clean, after_actions)
        )

    if discovery.type == "easy":
        return [
            ConfigureFastDDSEasyMode(
                easy_mode_base_address=discovery.easy.base_address,
            ),
        ]

    return [
        ConfigureFastDDS(
            with_discovery_server=False,
            discovery_server_ip="0.0.0.0",
            allowed_interfaces=[],
            simple_discovery=True,
        ),
        *then,
    ]
