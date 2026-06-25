from typing import Any
import pathlib

from jinja2 import Environment, FileSystemLoader

from launch.launch_context import LaunchContext
from launch.substitution import Substitution

from launch.some_substitutions_type import SomeSubstitutionsType

from launch.utilities import normalize_to_list_of_substitutions
from launch.utilities import perform_substitutions

from launch_ext.utilities import perform_substitutions_within_structure


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
            **{
                k: perform_substitutions_within_structure(context, v)
                for k, v in self.template_vars.items()
            }
        )

    def describe(self):
        return f"JinjaTemplate({self.template_path}, {self.template_vars})"
