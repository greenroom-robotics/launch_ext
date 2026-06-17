"""Make the ``launch`` 'latest' log symlink use a relative target.

Importing this module patches ``launch.logging._renew_latest_log_dir`` so the
``latest`` symlink points at the log directory's basename instead of its
absolute path. The log dir is always a sibling of ``latest``, so a relative
target resolves regardless of the absolute mount point -- e.g. when the log
directory is shared between a host and a Docker container under different paths.

Usage -- import the module and that's it::

    import launch_ext.patches.relative_latest_symlink  # noqa: F401

This works whenever *you* construct the ``LaunchService`` (custom entrypoints),
as long as the import runs first. For plain ``ros2 launch`` the LaunchService is
built before your launch file is imported; see ``launch_ext.ros2launch_options``
for the extension that applies this patch early enough in that path.
"""

import os

import launch.logging


def _renew_latest_log_dir_relative(*, log_dir):
    """
    Renew the 'latest' symlink using a relative target.

    Drop-in replacement for ``launch.logging._renew_latest_log_dir``.

    :param log_dir: the current logging directory
    :return: True if the link was successfully created/updated, False otherwise
    """
    base_dir = os.path.dirname(log_dir)
    latest_dir = os.path.join(base_dir, 'latest')

    if os.path.lexists(latest_dir):
        if not os.path.islink(latest_dir):
            return False
        os.unlink(latest_dir)
    os.symlink(
        os.path.basename(log_dir), latest_dir, target_is_directory=True)
    return True


def apply():
    """Install the patch (idempotent). Safe to call multiple times."""
    launch.logging._renew_latest_log_dir = _renew_latest_log_dir_relative


# Applied as a side effect of import so a bare ``import`` is enough.
apply()
