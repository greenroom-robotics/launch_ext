import time
from typing import Callable
from threading import Thread

import rclpy
from rclpy.node import Node
from launch import LaunchService, LaunchDescription
from example_interfaces.srv import Trigger
from example_interfaces.srv._trigger import Trigger_Request, Trigger_Response
from launch.logging import get_logger
from rclpy.executors import ExternalShutdownException


class SharedState:
    def __init__(self):
        self.launch_service = LaunchService()
        self.restarted_via_trigger = False
        self.launch_terminated = False


class TriggerNode(Node):
    def __init__(
        self,
        namespace: str,
        node_name: str,
        trigger_name: str,
        shared_state: SharedState,
    ):
        super().__init__(node_name, namespace=namespace)
        self.shared_state = shared_state
        self.srv = self.create_service(Trigger, "restart", self.trigger_callback)
        logger = get_logger("launch_with_restart_trigger")
        logger.info(f"Enabling restart for launch_service - {namespace}/{trigger_name}")

    def trigger_callback(self, request: Trigger_Request, response: Trigger_Response):
        logger = get_logger("launch_with_restart_trigger")
        logger.info("Restart launch_service triggered")
        if self.shared_state.launch_service is not None:
            self.shared_state.restarted_via_trigger = True
            self.shared_state.launch_service.shutdown()

            # Wait for the launch to terminate
            while not self.shared_state.launch_terminated:
                time.sleep(0.1)

            logger.info("Restart launch_service completed")
            response.success = True

            # Reset the flag
            self.shared_state.restarted_via_trigger = False

        else:
            logger.info("Launch service not yet started")
            response.success = False

        return response


def launch_with_restart_trigger(
    namespace: str,
    node_name: str,
    generate_launch_description: Callable[[], LaunchDescription],
    trigger_name="restart",
):
    """
    Launches a ROS description with a trigger service that can be used to restart the launch.


    ```python
    from launch_ext import launch_with_restart_trigger
    from gama_config.gama_vessel import read_vessel_config, Mode
    from .some_launch_description import generate_launch_description

    launch_with_restart_trigger(
        namespace=config.namespace_vessel,
        node_name="gama_bringup",
        trigger_name="restart",
        generate_launch_description=generate_launch_description
    )

    # This will make a `example_interfaces/srv/Trigger` service available at "/gama_bringup/restart"
    ```
    """
    rclpy.init()

    logger = get_logger("launch_with_restart_trigger")

    def run_ros(shared_state: SharedState):
        try:
            node = TriggerNode(
                namespace=namespace,
                node_name=node_name,
                trigger_name=trigger_name,
                shared_state=shared_state,
            )
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        except ExternalShutdownException:
            pass

    def run_launch(shared_state: SharedState):
        while True:
            logger.info("Running launch service...")
            shared_state.launch_terminated = False
            shared_state.launch_service = LaunchService()
            shared_state.launch_service.include_launch_description(generate_launch_description())
            shared_state.launch_service.run()
            if shared_state.restarted_via_trigger:
                logger.info("Launch shutdown due to trigger. Restarting...")
                shared_state.launch_terminated = True
                time.sleep(
                    0.5
                )  # Give the "while not self.shared_state.launch_terminated" some time...
                continue
            else:
                logger.info("Launch shutdown due to user.")
                break

    try:
        shared_state = SharedState()
        run_ros_thread = Thread(target=run_ros, args=(shared_state,))
        run_ros_thread.start()
        run_launch(shared_state)
    except KeyboardInterrupt:
        pass
    except ExternalShutdownException:
        pass
