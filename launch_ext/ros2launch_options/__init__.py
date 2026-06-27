"""``ros2launch.option`` extensions provided by launch_ext.

These are loaded and run by ``ros2 launch`` before the ``LaunchService`` is
constructed, which is the only hook early enough to patch behaviour (such as the
'latest' log symlink) that ``LaunchService`` triggers on creation.
"""
