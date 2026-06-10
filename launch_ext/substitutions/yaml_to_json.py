"""Module for the YamlToJson substitution."""

import json

import yaml
from launch.launch_context import LaunchContext
from launch.substitution import Substitution


class YamlToJson(Substitution):
    """Substitution that takes a FileContent substitution and converts YAML to JSON string."""

    def __init__(self, file_content_substitution: Substitution, quote_output: bool = True):
        """Create a YamlToJson substitution.

        Args:
            file_content_substitution: Substitution that provides YAML content
            quote_output: Whether to wrap the JSON output in single quotes (default: True)
        """
        super().__init__()
        self.file_content_substitution = file_content_substitution
        self.quote_output = quote_output

    def describe(self) -> str:
        """Return a description of this substitution as a string."""
        sub = self.file_content_substitution
        sub_desc = f"{type(sub).__name__}({sub.describe()})"
        return f"YamlToJson(file_content={sub_desc}, quote_output={self.quote_output})"

    def perform(self, context: LaunchContext) -> str:
        """Convert YAML content to JSON string."""
        yaml_content = self.file_content_substitution.perform(context)
        try:
            parsed_yaml = yaml.safe_load(yaml_content)
            json_output = json.dumps(parsed_yaml)
            return f"'{json_output}'" if self.quote_output else json_output
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML content: {e}")
