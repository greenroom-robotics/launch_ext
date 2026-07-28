from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext
from launch_ext.actions import IncludePackageLaunchFile


def test_include_package_launch_file():
    lc = LaunchContext()

    act = IncludePackageLaunchFile("launch", "launch_file.py")
    expected = f"{get_package_share_directory('launch')}/launch/launch_file.py"
    assert (
        act.launch_description_source._LaunchDescriptionSource__location[0].perform(lc)
        == expected
    )
