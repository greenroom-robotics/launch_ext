from launch.substitutions import EnvironmentVariable

def ROSDistro() -> EnvironmentVariable:
    """Substitution for the current ROS distribution."""
    return EnvironmentVariable("ROS_DISTRO")
