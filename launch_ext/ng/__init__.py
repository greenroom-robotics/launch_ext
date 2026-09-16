"""The `ng` middleware interface, introduced in 2.0.0.

The top-level `launch_ext.actions`, `launch_ext.discovery` and
`launch_ext.substitutions` modules carry the pre-2.0 middleware interface. This
package carries the newer one under the same symbol names.
"""

from . import actions
from . import discovery
from . import substitutions

__all__ = [
    "actions",
    "discovery",
    "substitutions",
]
