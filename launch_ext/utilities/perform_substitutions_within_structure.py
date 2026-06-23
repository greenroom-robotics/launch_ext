"""Utility for performing substitutions while preserving container structure."""

from typing import Any

from launch.launch_context import LaunchContext
from launch.substitution import Substitution
from launch.utilities import normalize_to_list_of_substitutions
from launch.utilities import perform_substitutions


def perform_substitutions_within_structure(context: LaunchContext, structure: Any) -> Any:
    """Recursively perform substitutions within a (possibly nested) structure.

    Unlike :func:`launch.utilities.perform_substitutions`, which merges a list of
    substitutions into a single string, this keeps the structure (``dict``,
    ``list``, ``tuple``) intact and only performs the substitutions found in the
    keys and values.

    Args:
        context: Launch context used to resolve substitutions.
        structure: An arbitrarily nested structure of containers, substitutions
            and plain values.

    Returns:
        A structure of the same shape where each substitution (and string) has
        been resolved to a string. Any other leaf value (``int``, ``float``,
        ``bool``, ``None``, ...) is returned unchanged.
    """
    if isinstance(structure, Substitution):
        return perform_substitutions(context, [structure])
    if isinstance(structure, str):
        return perform_substitutions(context, normalize_to_list_of_substitutions(structure))
    if isinstance(structure, dict):
        return {
            perform_substitutions_within_structure(
                context, key
            ): perform_substitutions_within_structure(context, value)
            for key, value in structure.items()
        }
    if isinstance(structure, tuple):
        return tuple(
            perform_substitutions_within_structure(context, item) for item in structure
        )
    if isinstance(structure, list):
        return [perform_substitutions_within_structure(context, item) for item in structure]
    return structure
