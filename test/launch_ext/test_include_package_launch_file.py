import os

from launch import LaunchContext
from launch_ext.actions import IncludePackageLaunchFile


def test_include_package_launch_file():
    lc = LaunchContext()

    act = IncludePackageLaunchFile("launch", "launch_file.py")
    distro = os.environ["ROS_DISTRO"]
    assert (
        act.launch_description_source._LaunchDescriptionSource__location[0].perform(lc)
        == f"/opt/ros/{distro}/share/launch/launch/launch_file.py"
    )
