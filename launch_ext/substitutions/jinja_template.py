from typing import Any
import pathlib

from jinja2 import Environment, FileSystemLoader

from launch.launch_context import LaunchContext
from launch.substitution import Substitution

from launch.some_substitutions_type import SomeSubstitutionsType

from launch.utilities import normalize_to_list_of_substitutions
from launch.utilities import perform_substitutions

class JinjaTemplate(Substitution):
    """Substitution that renders a Jinja2 template."""

    def __init__(
        self,
        template_path: SomeSubstitutionsType,
        template_vars: dict[SomeSubstitutionsType, SomeSubstitutionsType | Any] | None = None,
    ):
        self.template_path = normalize_to_list_of_substitutions(template_path)
        self.template_vars = template_vars or {}

    def perform(self, context: LaunchContext) -> str:
        template_path_str = pathlib.Path(perform_substitutions(context, self.template_path))

        env = Environment(
            loader=FileSystemLoader(template_path_str.parent),
            keep_trailing_newline=True,
        )
        template = env.get_template(template_path_str.name)

        return template.render(
            **{k: self._resolve_value(context, v) for k, v in self.template_vars.items()}
        )

    @staticmethod
    def _resolve_value(context: LaunchContext, value: SomeSubstitutionsType | Any) -> Any:
        """Resolve a template variable value.

        Strings and substitutions are performed against the launch context and
        rendered to a string. Any other object (e.g. a list, tuple or int) is
        passed through unchanged so the template can use it directly.
        """
        if isinstance(value, (str, Substitution)):
            return perform_substitutions(context, normalize_to_list_of_substitutions(value))
        return value

    def describe(self):
        return f"JinjaTemplate({self.template_path}, {self.template_vars})"
