import os

import launch.logging
import pytest

import launch_ext.patches.relative_latest_symlink as relsym
from launch_ext.ros2launch_options.relative_latest_symlink import (
    RelativeLatestSymlinkOption,
)


@pytest.fixture(autouse=True)
def restore_renew():
    """Restore launch's original function after each test."""
    saved = launch.logging._renew_latest_log_dir
    yield
    launch.logging._renew_latest_log_dir = saved


def test_import_applies_patch():
    # Importing the module (done at file top) is enough to install the patch.
    assert (
        launch.logging._renew_latest_log_dir
        is relsym._renew_latest_log_dir_relative
    )


def test_apply_reassigns_and_is_idempotent():
    launch.logging._renew_latest_log_dir = lambda **kw: None
    relsym.apply()
    assert (
        launch.logging._renew_latest_log_dir
        is relsym._renew_latest_log_dir_relative
    )
    # Calling again is harmless.
    relsym.apply()
    assert (
        launch.logging._renew_latest_log_dir
        is relsym._renew_latest_log_dir_relative
    )


def test_ros2launch_option_prestart_applies_patch():
    # Simulate what ros2launch does before constructing the LaunchService.
    launch.logging._renew_latest_log_dir = lambda **kw: None
    RelativeLatestSymlinkOption().prestart(args=None)
    assert (
        launch.logging._renew_latest_log_dir
        is relsym._renew_latest_log_dir_relative
    )


def test_symlink_target_is_relative(tmp_path):
    relsym.apply()
    log_dir = tmp_path / '2026-06-17-12-00-00-000000-host-1234'
    log_dir.mkdir()

    ok = launch.logging._renew_latest_log_dir(log_dir=str(log_dir))
    assert ok is True

    latest = tmp_path / 'latest'
    target = os.readlink(str(latest))
    # Relative target (just the basename), not an absolute path.
    assert target == log_dir.name
    assert not os.path.isabs(target)
    # And it still resolves to the real log directory.
    assert os.path.realpath(str(latest)) == os.path.realpath(str(log_dir))


def test_renews_existing_symlink(tmp_path):
    relsym.apply()
    first = tmp_path / 'run-1'
    second = tmp_path / 'run-2'
    first.mkdir()
    second.mkdir()

    assert launch.logging._renew_latest_log_dir(log_dir=str(first)) is True
    assert launch.logging._renew_latest_log_dir(log_dir=str(second)) is True

    latest = tmp_path / 'latest'
    assert os.readlink(str(latest)) == second.name


def test_refuses_when_latest_is_not_a_symlink(tmp_path):
    relsym.apply()
    # A real directory named 'latest' must not be clobbered.
    (tmp_path / 'latest').mkdir()
    log_dir = tmp_path / 'run-1'
    log_dir.mkdir()

    assert launch.logging._renew_latest_log_dir(log_dir=str(log_dir)) is False
