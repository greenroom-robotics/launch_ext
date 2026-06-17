"""``ros2launch.option`` extension: relative 'latest' log symlink.

Registered under the ``ros2launch.option`` entry point group. ``ros2launch``
instantiates every such extension and calls ``prestart()`` *before* it builds
the ``LaunchService`` (ros2launch/api/api.py) -- and the LaunchService creates
the 'latest' symlink on construction. Applying the patch in ``prestart()`` is
therefore early enough to take effect for ``ros2 launch <pkg> <file>``.

This extension is always on: once launch_ext is installed, every ``ros2 launch``
invocation gets the relative-symlink behaviour.
"""

from ros2launch.option import OptionExtension

from launch_ext.patches import relative_latest_symlink


class RelativeLatestSymlinkOption(OptionExtension):
    """Make the 'latest' log symlink relative for every ``ros2 launch`` run."""

    def prestart(self, args):
        relative_latest_symlink.apply()
