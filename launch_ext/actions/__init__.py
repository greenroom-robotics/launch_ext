"""Launch actions for extended functionality.

This module provides additional launch actions beyond those available in the core
launch package, including process execution extensions, device node creation,
git repository management, and configuration utilities for middleware like
Zenoh and FastDDS.
"""

from .log_rotate import LogRotate
from .include_package_launch_file import IncludePackageLaunchFile
from .make_device_node import MakeDeviceNode, MakeDeviceNodeFromPath
from .write_file import WriteFile
from .set_launch_configuration_if_not_none import SetLaunchConfigurationIfNotNone
from .git_repo_info import LogRepoInfo, VerifyRepoCommit, VerifyRepoClean, SaveRepoDiff
from .configure_fastdds import ConfigureFastDDS
from .configure_fastdds_easy import ConfigureFastDDSEasyMode
from .configure_zenoh import ConfigureZenoh
from .configure_avahi import ConfigureAvahi, AvahiProductService
from .execute_after_process_output import ExecuteAfterProcessOutput
from .execute_and_after_process_exit import ExecuteAndAfterProcessExit

from .execute_local import ExecuteLocalExt
from .execute_process import ExecuteProcessExt

__all__ = [
    "LogRotate",
    "IncludePackageLaunchFile",
    "WriteFile",
    "SetLaunchConfigurationIfNotNone",
    "ExecuteLocalExt",
    "ExecuteProcessExt",
    "MakeDeviceNode",
    "MakeDeviceNodeFromPath",
    "LogRepoInfo",
    "VerifyRepoCommit",
    "VerifyRepoClean",
    "SaveRepoDiff",
    "ConfigureFastDDS",
    "ConfigureFastDDSEasyMode",
    "ConfigureZenoh",
    "ConfigureAvahi",
    "AvahiProductService",
    "ExecuteAfterProcessOutput",
    "ExecuteAndAfterProcessExit",
]
