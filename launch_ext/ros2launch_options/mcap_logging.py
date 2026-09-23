"""``ros2launch.option`` extension: write launch logs to MCAP when enabled.

Registered under the ``ros2launch.option`` entry point group; ``prestart()`` runs
before ``ros2 launch`` builds the ``LaunchService`` (which opens the main log), so
it is early enough to swap the log handler factory.

Off by default. Set ``LAUNCH_LOG_MCAP`` to ``1``/``true``/``yes``/``on`` to enable.
"""

import os

from ros2launch.option import OptionExtension

ENV_VAR = "LAUNCH_LOG_MCAP"


def enabled():
    """Whether ``LAUNCH_LOG_MCAP`` asks for MCAP logging."""
    return os.environ.get(ENV_VAR, "").strip().lower() in ("1", "true", "yes", "on")


class McapLoggingOption(OptionExtension):
    """Swap launch's log files for a single MCAP file when ``LAUNCH_LOG_MCAP`` is set."""

    def prestart(self, args):
        if enabled():
            # Imported here so a missing ``mcap`` only matters when enabled -- and
            # then fails loudly instead of silently writing no logs.
            from ..patches import mcap_logging

            mcap_logging.apply()
