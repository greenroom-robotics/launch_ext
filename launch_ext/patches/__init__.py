"""Opt-in monkey patches for the upstream ``launch`` package.

Each module under this package applies a single patch as a side effect of being
imported. Importing this package does **not** apply anything -- import the
specific patch you want, e.g.::

    import launch_ext.patches.relative_latest_symlink  # noqa: F401
"""
