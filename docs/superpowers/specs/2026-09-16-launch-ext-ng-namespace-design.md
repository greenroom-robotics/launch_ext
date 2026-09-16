# Restoring the pre-2.0 middleware interface alongside an `ng` namespace

Date: 2026-09-16
Status: approved, not yet implemented
Target release: 2.1.0

## Problem

`2.0.0` (commit `575ad01`, `feat!: fastdds profiles, jinja templates, RestartableAction, ros2 msg, srvs`)
replaced the FastDDS/middleware interface in place. Consumers pinned to `1.27.0` cannot move to
`2.x` without rewriting their launch files, and cannot take any of the unrelated `2.x` additions
(`JinjaTemplate`, `Restartable`, the ROS event/service actions) without taking the middleware
rewrite with them.

What `2.0.0` changed:

- **Removed:** `ConfigureFastDDSEasyMode`, `FastDDSSuperclientEnvironment`,
  `get_fastdds_superclient_environment`, `discovery.discovery_config.Discovery` and its
  `DiscoverySimple` / `DiscoveryFastDDS` / `DiscoveryZenoh` / `DiscoveryEasy` models.
- **Renamed:** `FastDDSClientEnvironment` to `FastDDSClientPath` (the class is otherwise identical).
- **Same name, new signature:** `configure_middleware(discovery, with_server=)` to
  `(middleware_config, inherit=)`; `ConfigureFastDDS(with_discovery_server, discovery_server_ip,
  allowed_interfaces, simple_discovery)` to `(discovery_protocol, external_interfaces,
  local_discovery_server, domain_id, inherit)`; `ConfigureZenoh(with_router=)` to `(run_router=)`,
  which also moved where `ZENOH_SESSION_CONFIG_URI` is set.
- **Same path, new contents:** `launch_ext/config/fastdds_profile.xml.j2`, whose template variables
  differ between the two generations.

Both known consumers still build the `1.27.0` config shape: gama's `libs/gama_config` and lookout's
`packages/lookout_config/lookout_config/types.py` each define their own structural copy of
`Discovery` (`.type`, `.fastdds.with_discovery_server`, `.zenoh.with_router`). Neither constructs a
`MiddlewareConfig`. Lookout imports the top-level `configure_middleware` while running `2.x`, so
that call currently raises `AttributeError` on `.middleware`.

## Goals

- Restore the `1.27.0` interface at its original import paths, unchanged.
- Keep the `2.x` middleware interface available, under `launch_ext.ng`.
- Let a consumer on either generation use the non-middleware `2.x` additions.

## Non-goals

- No translation layer, dispatcher or adapter between the two generations.
- No behaviour changes to either generation.
- No deprecation timeline for the restored interface. That is a later decision.

## Design

### Layout

Top level is `1.27.0` restored verbatim. The `2.x` middleware code moves under `launch_ext/ng/`,
keeping its symbol names — the namespace is the only thing that distinguishes them.

```
launch_ext/
  actions/configure_fastdds.py                     <- restored from 1.27.0
  actions/configure_fastdds_easy.py                <- restored from 1.27.0
  actions/configure_zenoh.py                       <- restored from 1.27.0
  discovery/configure_middleware.py                <- restored from 1.27.0
  discovery/discovery_config.py                    <- restored from 1.27.0
  substitutions/fastdds_superclient_environment.py <- restored from 1.27.0
  config/fastdds_profile.xml.j2                    <- restored from 1.27.0
  ng/
    actions/configure_fastdds.py                   <- current 2.x
    actions/configure_zenoh.py                     <- current 2.x
    discovery/configure_middleware.py              <- current 2.x
    discovery/middleware_config.py                 <- current 2.x
    substitutions/fastdds_profile.py               <- current 2.x
    config/fastdds_profile.xml.j2                  <- current 2.x
```

```python
from launch_ext.discovery import configure_middleware       # 1.27.0
from launch_ext.ng.discovery import configure_middleware    # 2.x

from launch_ext.actions import ConfigureFastDDS             # 1.27.0
from launch_ext.ng.actions import ConfigureFastDDS          # 2.x
```

### What forks, what stays shared

Only the middleware surface forks. Everything else stays at top level and serves both generations:
`JinjaTemplate`, `Restartable`, `SubscribeRosTopic`, `ServeROSService`, `EmitEventOnTriggerService`,
`events`, `event_handlers`, `utilities`, `ROSDistro`, `ResolveHost`, `WriteFile`,
`ExecuteAfterProcessOutput`, `ExecuteAndAfterProcessExit`, `fastdds_env_var`, `configure_avahi`,
the Zenoh JSON configs.

`FastDDSClientPath` and `FastDDSClientEnvironment` are the same class under two names, so
`substitutions/fastdds_client_environment.py` does not fork: it keeps `FastDDSClientPath` and adds
`FastDDSClientEnvironment` as an alias. `get_fastdds_client_environment` is unchanged and shared.

### Export surfaces

- `launch_ext/__init__.py`: add `ng`.
- `launch_ext/actions/__init__.py`: re-add `ConfigureFastDDSEasyMode`; `ConfigureFastDDS` and
  `ConfigureZenoh` now resolve to the restored modules; keep the `2.x` non-middleware exports.
- `launch_ext/substitutions/__init__.py`: re-add `FastDDSSuperclientEnvironment`,
  `get_fastdds_superclient_environment` and the `FastDDSClientEnvironment` alias; drop
  `FastDDSProfile`, which moves to `launch_ext.ng.substitutions`; keep `JinjaTemplate`, `ROSDistro`,
  `FastDDSClientPath`, `FastDDSEnvVar`, `get_fastdds_default_profile_env_var`.
- `launch_ext/discovery/__init__.py`: back to the `1.27.0` contents, exporting `configure_middleware`
  only. `Discovery` is imported from `launch_ext.discovery.discovery_config`, as it was at `1.27.0`.
- `launch_ext/ng/{actions,discovery,substitutions}/__init__.py`: export the moved symbols under
  their existing names.

### Relative imports in the moved modules

Moving a module one level deeper changes what `..` reaches. In `ng`, imports of shared code gain a
level; imports of `ng`'s own siblings do not:

- `ng/actions/configure_fastdds.py`: `.write_file` and `.execute_after_process_output` become
  `...actions.write_file` / `...actions.execute_after_process_output`; `..substitutions` becomes
  `...substitutions` for the shared names and `..substitutions` for ng's `FastDDSProfile`;
  `..events` becomes `...events`; `..discovery.middleware_config` stays within `ng`.
- `ng/substitutions/fastdds_profile.py`: `.resolve_host`, `.ros_distro` and `.jinja_template` become
  `...substitutions.*`; `..discovery.middleware_config` stays within `ng`.
- `ng/discovery/configure_middleware.py`: keeps its lazy imports of `..actions.*` (now ng's own
  actions) — the circular-import guard the current code documents still applies.

### Packaging

- `setup.py`: `find_packages` picks up `launch_ext.ng.*` automatically; add a `data_files` entry
  installing `launch_ext/ng/config/*` to `share/launch_ext/config/ng`.
- `ng`'s `FastDDSProfile` resolves its template at `share/launch_ext/config/ng/fastdds_profile.xml.j2`;
  the restored `FastDDSProfileSubstitution` keeps building its jinja2 `Environment` rooted at
  `share/launch_ext/config/`.
- Version to `2.1.0` in both `setup.py` and `package.xml`.

### Tests

- Move `test/launch_ext/test_configure_middleware.py` and `test_fastdds_profile.py` to
  `test/launch_ext/ng/`, updating imports to `launch_ext.ng.*`. Their assertions do not change.
- Add a smoke test for the restored interface: `configure_middleware(Discovery(type="fastdds"))` and
  `Discovery(type="zenoh")` each build their expected entity list, and
  `get_fastdds_superclient_environment` returns the superclient profile env var.
- Add an import test asserting both `configure_middleware` functions are importable side by side and
  are distinct objects.

## Consumer impact

- **gama** (pinned `1.27.0`): no import changes. Bumping its `package.xml` pin to `2.1.0` gives it
  `JinjaTemplate` while its middleware calls keep working.
- **lookout**: no import changes, and its `configure_middleware(config.discovery, ...)` call becomes
  correct again, since the top-level function once more accepts the `Discovery` shape
  `lookout_config` builds. It moves to `launch_ext.ng` only when it adopts `MiddlewareConfig`.

## Risks

- `2.x` code outside gama, lookout and platform that imports `ConfigureFastDDS`, `ConfigureZenoh` or
  `configure_middleware` from the top level will bind to the restored implementation and break. A
  grep across those three repos found no such caller, but the search was not exhaustive; hence the
  release note should state the move explicitly.
- Two `fastdds_profile.xml.j2` files now exist. A fix applied to one does not reach the other, and
  nothing enforces that. Accepted for as long as both generations are supported.
