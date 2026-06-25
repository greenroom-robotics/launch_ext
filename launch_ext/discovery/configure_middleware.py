from launch.actions import ExecuteProcess, RegisterEventHandler
from launch.launch_description_entity import LaunchDescriptionEntity
from launch.some_entities_type import SomeEntitiesType
from launch.utilities import normalize_to_list_of_entities


from ..discovery.middleware_config import MiddlewareConfig, MiddlewareTypes, FastDDSDiscoveryType

from ..event_handlers import OnActionReady


def configure_middleware(
    middleware_config: MiddlewareConfig,
    inherit: bool = False,
    then: SomeEntitiesType | None = None,
) -> list[LaunchDescriptionEntity]:
    """
    Configure the middleware from configuration structure.

    Args:
        middleware_config: The middleware configuration to use.
        inherit: Inherit an already configured middleware setup. Do not run anything.
        then: Additional launch entities to execute after the middleware is configured.
    """

    # Imported lazily to avoid a circular import: the ``actions`` package
    # pulls in ``substitutions`` -> ``discovery`` -> this module.
    from ..actions.configure_zenoh import deep_merge, ConfigureZenoh
    from ..actions.configure_fastdds import ConfigureFastDDS, FastDDSDiscoveryServer
    from ..actions.execute_and_after_process_exit import ExecuteAndAfterProcessExit

    then = normalize_to_list_of_entities([then] if then else [])

    if middleware_config.middleware == MiddlewareTypes.ZENOH:
        # Merge router_peers into router_config connect/endpoints
        if middleware_config.zenoh.router_peers:
            peer_endpoints = [f"tcp/{peer}:7447" for peer in middleware_config.zenoh.router_peers]
            middleware_config.zenoh.router_config = deep_merge(
                middleware_config.zenoh.router_config,
                {"connect": {"endpoints": peer_endpoints}},
            )

        return [
            ConfigureZenoh(
                run_router=middleware_config.zenoh.run_router and not inherit,
                router_config=middleware_config.zenoh.router_config,
                session_config=middleware_config.zenoh.session_config,
                generate_router_config_file=True and not inherit,
                generate_session_config_file=True and not inherit,
            ),
        ] + then

    if middleware_config.middleware == MiddlewareTypes.FASTDDS:
        if middleware_config.fastdds.discovery_type == FastDDSDiscoveryType.DISCOVERY_SERVER:
            discovery_protocol = "CLIENT"
        elif middleware_config.fastdds.discovery_type == FastDDSDiscoveryType.EASY:
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
            inherit=inherit,
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

        if middleware_config.fastdds.run_discovery_server and not inherit:
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

        if inherit:
            # If inheriting, we don't need to stop the ROS2 daemon or clean shared memory.
            return after_clean_actions

        return ExecuteAndAfterProcessExit(
            stop_ros2_daemon, ExecuteAndAfterProcessExit(shm_clean, after_clean_actions)
        )

    raise NotImplementedError(
        f"Discovery middleware '{middleware_config.middleware}' is not supported yet"
    )
