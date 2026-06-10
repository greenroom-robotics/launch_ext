from launch.actions import ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_entity import LaunchDescriptionEntity
from launch.some_entities_type import SomeEntitiesType


def ExecuteAndAfterProcessExit(
    target_process: ExecuteProcess, then: SomeEntitiesType
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
