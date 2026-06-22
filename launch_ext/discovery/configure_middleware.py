from typing import Literal
from launch.actions import SetLaunchConfiguration, ExecuteProcess, RegisterEventHandler
from launch.launch_description_entity import LaunchDescriptionEntity
from launch.some_entities_type import SomeEntitiesType
from launch.utilities import normalize_to_list_of_entities


from launch_ext.actions.configure_zenoh import deep_merge
from launch_ext.discovery.discovery_config import Discovery

from launch_ext.actions.configure_fastdds import ConfigureFastDDS, FastDDSDiscoveryServer
from launch_ext.actions.configure_zenoh import ConfigureZenoh
from launch_ext.actions.execute_and_after_process_exit import ExecuteAndAfterProcessExit
from launch_ext.event_handlers import OnActionReady


def configure_middleware(
    discovery_config: Discovery,
    run_server = True,
    then: SomeEntitiesType | None = None,
) -> list[LaunchDescriptionEntity]:
    then = normalize_to_list_of_entities([then] if then else [])

    if discovery_config.middleware == "zenoh":
        zenoh = discovery_config.zenoh
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
                with_router=zenoh.with_router and run_server,
                router_config=router_config,
                session_config=session_config,
                generate_router_config_file=True,
                generate_session_config_file=True,
            ),
        ] + then

    if discovery_config.middleware == "fastdds":
        if discovery_config.fastdds.discovery_type == "discovery_server":
            discovery_protocol = "CLIENT"
        else:
            discovery_protocol = discovery_config.fastdds.discovery_type.upper()

        cfg = ConfigureFastDDS(
            discovery_protocol=discovery_protocol,
            external_interfaces=discovery_config.fastdds.external_interfaces,
            ros_domain_id=discovery_config.ros_domain_id,
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

        if run_server:
            ds = FastDDSDiscoveryServer(
                external_interfaces=discovery_config.fastdds.external_interfaces,
                external_discovery_servers=discovery_config.fastdds.external_discovery_servers,
                ros_domain_id=discovery_config.ros_domain_id,
            )

            after_clean_actions = [
                cfg,
                RegisterEventHandler(
                    OnActionReady(target_action=ds.discovery_server, on_ready=then)
                ),
                ds,
            ]
        else:
            after_clean_actions = [cfg] + then

        return ExecuteAndAfterProcessExit(
            stop_ros2_daemon, ExecuteAndAfterProcessExit(shm_clean, after_clean_actions)
        )

    raise NotImplementedError(f"Discovery type '{discovery_config.type}' is not supported yet")

