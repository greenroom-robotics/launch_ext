"""Template-based string substitution using Python's string.Template.

This module provides a substitution class that enables template-based string
replacement using launch configurations as template variables.
"""

from typing import List

from string import Template

from launch.launch_context import LaunchContext
from launch.substitution import Substitution
from launch.some_substitutions_type import SomeSubstitutionsType
from launch.utilities import normalize_to_list_of_substitutions
from launch.utilities import perform_substitutions


class Templated(Substitution):
    """Template-based substitution using Python's string.Template syntax.

    This substitution class allows for template strings with variables that
    are replaced with launch configuration values. Template variables are
    specified using ${variable_name} syntax.

    Example:
        Templated("Hello ${name}, mode is ${mode}")

    The variables 'name' and 'mode' will be replaced with their corresponding
    launch configuration values.
    """

    def __init__(self, template: SomeSubstitutionsType) -> None:
        """Initialize the Templated substitution.

        Args:
            template: Template string containing variable placeholders
        """
        super().__init__()

        self.__template = normalize_to_list_of_substitutions(template)

    @property
    def raw_template(self) -> List[Substitution]:
        """Get the raw template as a list of substitutions.

        Returns:
            List of substitution objects representing the template
        """
        return self.__template

    def describe(self) -> str:
        """Return a description of this substitution as a string.

        Returns:
            String representation of the template for debugging purposes
        """
        return f"'{self.raw_template}'"

    def perform(self, context: LaunchContext) -> str:
        """Perform the substitution by replacing template variables.

        Uses Python's string.Template to substitute variables with their
        corresponding values from the launch context configuration.

        Args:
            context: Launch context containing configuration values

        Returns:
            String with template variables replaced by their values

        Raises:
            KeyError: If a template variable is not found in launch configurations
        """
        temp = Template(perform_substitutions(context, self.raw_template))
        return temp.substitute(context.launch_configurations)
