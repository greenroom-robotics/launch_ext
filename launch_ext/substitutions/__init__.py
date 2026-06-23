"""Launch substitutions for enhanced text processing.

This module provides substitution classes that extend the capabilities of the
core launch substitution system, including template processing, temporary file
creation, YAML/JSON conversion, and host resolution utilities.
"""

from .templated import Templated
from .unary import Unary
from .write_temp_file import WriteTempFile
from .yaml_to_file import YAMLToFile
from .yaml_to_json import YamlToJson
from .xacro import Xacro
from .resolve_host import ResolveHost
from .fastdds_superclient_environment import (
    FastDDSSuperclientEnvironment,
    get_fastdds_superclient_environment,
)
from .fastdds_client_environment import FastDDSClientEnvironment, get_fastdds_client_environment
from .fastdds_env_var import FastDDSEnvVar, get_fastdds_default_profile_env_var
from .fastdds_profile import FastDDSProfile
from .jinja_template import JinjaTemplate
from .ros_distro import ROSDistro

# Alias for consistent naming
YamlToFile = YAMLToFile

__all__ = [
    "Templated",
    "Unary",
    "WriteTempFile",
    "YAMLToFile",
    "YamlToFile",
    "YamlToJson",
    "Xacro",
    "ResolveHost",
    "FastDDSSuperclientEnvironment",
    "FastDDSClientEnvironment",
    "get_fastdds_superclient_environment",
    "get_fastdds_client_environment",
    "FastDDSEnvVar",
    "get_fastdds_default_profile_env_var",
    "FastDDSProfile",
    "JinjaTemplate",
    "ROSDistro",
]
