from launch.actions import SetLaunchConfiguration, ExecuteProcess, RegisterEventHandler
from launch.launch_description_entity import LaunchDescriptionEntity
from launch.some_entities_type import SomeEntitiesType
from launch.utilities import normalize_to_list_of_entities


from ..discovery.middleware_config import MiddlewareConfig

from ..event_handlers import OnActionReady


def configure_middleware(
    middleware_config: MiddlewareConfig,
    run_server = True,
    then: SomeEntitiesType | None = None,
) -> list[LaunchDescriptionEntity]:
    # Imported lazily to avoid a circular import: the ``actions`` package
    # pulls in ``substitutions`` -> ``discovery`` -> this module.
    from ..actions.configure_zenoh import deep_merge, ConfigureZenoh
    from ..actions.configure_fastdds import ConfigureFastDDS, FastDDSDiscoveryServer
    from ..actions.execute_and_after_process_exit import ExecuteAndAfterProcessExit

    then = normalize_to_list_of_entities([then] if then else [])

    if middleware_config.middleware == "zenoh":
        zenoh = middleware_config.zenoh
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
                run_router=zenoh.run_router and run_server,
                router_config=router_config,
                session_config=session_config,
                generate_router_config_file=True,
                generate_session_config_file=True,
            ),
        ] + then

    if middleware_config.middleware == "fastdds":
        if middleware_config.fastdds.discovery_type == "discovery_server":
            discovery_protocol = "CLIENT"
        elif middleware_config.fastdds.discovery_type == "easy":
            raise NotImplementedError("Easy mode is not implemented yet")
            # discovery_protocol = "SIMPLE"
            # SetEnvironmentVariable(
            #     "ROS2_EASY_MODE",
            #     ResolveHost(easy_mode_base_address),
            # )
            # discovery_protocol = "EASY"
        else:
            # discovery_protocol = "SIMPLE"
            raise NotImplementedError("Simple mode is not implemented yet")

        cfg = ConfigureFastDDS(
            discovery_protocol=discovery_protocol,
            external_interfaces=middleware_config.fastdds.external_interfaces,
            local_discovery_server=middleware_config.fastdds.local_discovery_server,
            domain_id=middleware_config.ros_domain_id,
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
                external_interfaces=middleware_config.fastdds.external_interfaces,
                external_discovery_servers=middleware_config.fastdds.external_discovery_servers,
                local_discovery_server=middleware_config.fastdds.local_discovery_server,
                domain_id=middleware_config.ros_domain_id,
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

    raise NotImplementedError(
        f"Discovery middleware '{middleware_config.middleware}' is not supported yet"
    )

