from launch.actions import ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_entity import LaunchDescriptionEntity


def ExecuteAndAfterProcessExit(
    target_process: ExecuteProcess, then: list[LaunchDescriptionEntity]
) -> list[LaunchDescriptionEntity]:
    return [
        target_process,
        RegisterEventHandler(
            OnProcessExit(
                target_action=target_process,
                on_exit=then,
            )
        ),
    ]
