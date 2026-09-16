# launch_ext `ng` Namespace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the `1.27.0` FastDDS/middleware interface at its original import paths while keeping the `2.x` middleware interface available under `launch_ext.ng`, released as `2.1.0`.

**Architecture:** The `2.x` middleware modules are copied into a new `launch_ext/ng/` subpackage with their relative imports rewritten, then the `1.27.0` versions are checked out from the tag over the top-level paths they used to occupy. The two generations share every non-middleware module and never call each other — no adapter, no dispatcher, no shared config model.

**Tech Stack:** Python 3.12+, ROS 2 `launch` / `launch_ros`, pydantic v2, jinja2, pytest, colcon, pixi.

**Spec:** `docs/superpowers/specs/2026-09-16-launch-ext-ng-namespace-design.md`

## Global Constraints

- Restored files must be byte-identical to the `1.27.0` tag. Recover them with `git checkout 1.27.0 -- <path>`, never by hand-editing.
- The `2.x` middleware code keeps its symbol names in `ng`. No `ng_` or `NG` name prefixes — the namespace is the only distinguishing mark.
- No translation, dispatch or adapter between `Discovery` (old) and `MiddlewareConfig` (new).
- Only the middleware surface forks. `JinjaTemplate`, `Restartable`, `SubscribeRosTopic`, `ServeROSService`, `EmitEventOnTriggerService`, `events`, `event_handlers`, `utilities`, `ROSDistro`, `ResolveHost`, `WriteFile`, `ExecuteAfterProcessOutput`, `ExecuteAndAfterProcessExit`, `fastdds_env_var`, `configure_avahi` and the Zenoh JSON configs stay at top level, shared.
- `launch_ext` must remain importable at every commit. Never leave a commit where a top-level `__init__.py` imports a module that does not exist.
- Version is `2.1.0`, set in both `setup.py` and `package.xml`.
- Test commands: `pixi run pytest <path> -v` for a single file, `pixi run test` for the full colcon gate.

---

## File Structure

**Created:**

| File | Responsibility |
|---|---|
| `launch_ext/ng/__init__.py` | Expose `actions`, `discovery`, `substitutions` submodules |
| `launch_ext/ng/actions/__init__.py` | Export `ConfigureFastDDS`, `FastDDSDiscoveryServer`, `ConfigureZenoh` |
| `launch_ext/ng/actions/configure_fastdds.py` | 2.x FastDDS action, imports rewritten for the deeper package |
| `launch_ext/ng/actions/configure_zenoh.py` | 2.x Zenoh action (no relative imports; copied as-is) |
| `launch_ext/ng/discovery/__init__.py` | Export `configure_middleware` and the middleware config models |
| `launch_ext/ng/discovery/configure_middleware.py` | 2.x entry point taking `MiddlewareConfig` |
| `launch_ext/ng/discovery/middleware_config.py` | 2.x pydantic models (copied as-is) |
| `launch_ext/ng/substitutions/__init__.py` | Export `FastDDSProfile` |
| `launch_ext/ng/substitutions/fastdds_profile.py` | 2.x profile substitution, pointing at the ng template |
| `launch_ext/ng/config/fastdds_profile.xml.j2` | 2.x template (copied as-is) |
| `test/launch_ext/ng/test_configure_middleware.py` | Moved 2.x test, ng imports |
| `test/launch_ext/ng/test_fastdds_profile.py` | Moved 2.x test, ng imports |
| `test/launch_ext/test_configure_middleware_legacy.py` | Smoke tests for the restored interface |
| `test/launch_ext/test_namespace_coexistence.py` | Asserts both generations import side by side and stay distinct |

**Restored from the `1.27.0` tag:** `launch_ext/actions/configure_fastdds.py`, `launch_ext/actions/configure_fastdds_easy.py`, `launch_ext/actions/configure_zenoh.py`, `launch_ext/discovery/configure_middleware.py`, `launch_ext/discovery/discovery_config.py`, `launch_ext/substitutions/fastdds_superclient_environment.py`, `launch_ext/config/fastdds_profile.xml.j2`.

**Deleted:** `launch_ext/discovery/middleware_config.py`, `launch_ext/substitutions/fastdds_profile.py` (both live on in `ng`).

**Modified:** `launch_ext/__init__.py`, `launch_ext/actions/__init__.py`, `launch_ext/substitutions/__init__.py`, `launch_ext/substitutions/fastdds_client_environment.py`, `setup.py`, `package.xml`, `README.md`.

---

## Task 1: Create the `ng` subpackage

Copies the 2.x middleware modules into `launch_ext/ng/`, rewrites their relative imports, moves their tests, and installs the ng template. The top-level 2.x code is left untouched by this task, so the package keeps importing and the moved tests prove `ng` works before anything is restored over the originals.

**Files:**
- Create: `launch_ext/ng/__init__.py`, `launch_ext/ng/actions/__init__.py`, `launch_ext/ng/discovery/__init__.py`, `launch_ext/ng/substitutions/__init__.py`
- Create (copied): `launch_ext/ng/actions/configure_fastdds.py`, `launch_ext/ng/actions/configure_zenoh.py`, `launch_ext/ng/discovery/configure_middleware.py`, `launch_ext/ng/discovery/middleware_config.py`, `launch_ext/ng/substitutions/fastdds_profile.py`, `launch_ext/ng/config/fastdds_profile.xml.j2`
- Modify: `launch_ext/__init__.py`, `setup.py:12-17`
- Test: `test/launch_ext/ng/test_configure_middleware.py`, `test/launch_ext/ng/test_fastdds_profile.py` (moved from `test/launch_ext/`)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `launch_ext.ng.actions.ConfigureFastDDS`, `launch_ext.ng.actions.FastDDSDiscoveryServer`, `launch_ext.ng.actions.ConfigureZenoh`, `launch_ext.ng.discovery.configure_middleware(middleware_config, inherit=False, then=None)`, `launch_ext.ng.discovery.{MiddlewareConfig, MiddlewareTypes, FastDDSDiscoveryType, FastDDSMiddleware, ZenohMiddleware, IPEndPoint, DEFAULT_FAST_DISCOVERY_SERVER_PORT}`, `launch_ext.ng.substitutions.FastDDSProfile`.

- [ ] **Step 1: Copy the modules into place**

```bash
cd /home/russ/work/launch_ext
mkdir -p launch_ext/ng/actions launch_ext/ng/discovery launch_ext/ng/substitutions launch_ext/ng/config
cp launch_ext/actions/configure_fastdds.py       launch_ext/ng/actions/configure_fastdds.py
cp launch_ext/actions/configure_zenoh.py         launch_ext/ng/actions/configure_zenoh.py
cp launch_ext/discovery/configure_middleware.py  launch_ext/ng/discovery/configure_middleware.py
cp launch_ext/discovery/middleware_config.py     launch_ext/ng/discovery/middleware_config.py
cp launch_ext/substitutions/fastdds_profile.py   launch_ext/ng/substitutions/fastdds_profile.py
cp launch_ext/config/fastdds_profile.xml.j2      launch_ext/ng/config/fastdds_profile.xml.j2
```

- [ ] **Step 2: Rewrite the relative imports in `launch_ext/ng/actions/configure_fastdds.py`**

One level deeper means `..` no longer reaches the shared packages. Replace lines 16-24:

```python
from ...actions.write_file import WriteFile
from ...actions.execute_after_process_output import ExecuteAfterProcessOutput
from ..substitutions import FastDDSProfile
from ...substitutions import get_fastdds_default_profile_env_var
from ...events import ActionReady

from ..discovery.middleware_config import IPEndPoint, DEFAULT_FAST_DISCOVERY_SERVER_PORT
```

Note the split: `FastDDSProfile` resolves to ng's own `substitutions`, `get_fastdds_default_profile_env_var` to the shared one. `..discovery.middleware_config` is unchanged — it now means `launch_ext.ng.discovery`.

`launch_ext/ng/actions/configure_zenoh.py` has no relative imports; leave it exactly as copied.

- [ ] **Step 3: Rewrite the relative imports and the template path in `launch_ext/ng/substitutions/fastdds_profile.py`**

Replace lines 6-11:

```python
from ...substitutions.resolve_host import ResolveHost
from ...substitutions.ros_distro import ROSDistro

from ...substitutions.jinja_template import JinjaTemplate

from ..discovery.middleware_config import IPEndPoint
```

Then point the template at the ng install directory — find the `JinjaTemplate(` call in `FastDDSProfile.__init__` and change its `template_path`:

```python
        self.jtemplate = JinjaTemplate(
            template_path=PathJoinSubstitution(
                [FindPackageShare("launch_ext"), "config", "ng", "fastdds_profile.xml.j2"]
            ),
            template_vars=self.template_vars,
        )
```

- [ ] **Step 4: Rewrite the relative imports in `launch_ext/ng/discovery/configure_middleware.py`**

The module-level imports become:

```python
from ..discovery.middleware_config import MiddlewareConfig, MiddlewareTypes, FastDDSDiscoveryType

from ...event_handlers import OnActionReady
```

and inside `configure_middleware`, the lazy import block becomes:

```python
    from ..actions.configure_zenoh import deep_merge, ConfigureZenoh
    from ..actions.configure_fastdds import ConfigureFastDDS, FastDDSDiscoveryServer
    from ...actions.execute_and_after_process_exit import ExecuteAndAfterProcessExit
```

`deep_merge`, `ConfigureZenoh`, `ConfigureFastDDS` and `FastDDSDiscoveryServer` come from ng's own actions; `ExecuteAndAfterProcessExit` is shared. Keep the comment explaining why these imports are lazy — the circular-import path it describes still exists inside `ng`.

- [ ] **Step 5: Write the `ng` package `__init__` files**

`launch_ext/ng/__init__.py`:

```python
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
```

`launch_ext/ng/actions/__init__.py`:

```python
from .configure_fastdds import ConfigureFastDDS, FastDDSDiscoveryServer
from .configure_zenoh import ConfigureZenoh

__all__ = [
    "ConfigureFastDDS",
    "FastDDSDiscoveryServer",
    "ConfigureZenoh",
]
```

`launch_ext/ng/discovery/__init__.py`:

```python
from .configure_middleware import configure_middleware
from .middleware_config import (
    DEFAULT_FAST_DISCOVERY_SERVER_PORT,
    FastDDSDiscoveryType,
    FastDDSMiddleware,
    IPEndPoint,
    MiddlewareConfig,
    MiddlewareTypes,
    ZenohMiddleware,
)

__all__ = [
    "configure_middleware",
    "DEFAULT_FAST_DISCOVERY_SERVER_PORT",
    "FastDDSDiscoveryType",
    "FastDDSMiddleware",
    "IPEndPoint",
    "MiddlewareConfig",
    "MiddlewareTypes",
    "ZenohMiddleware",
]
```

`launch_ext/ng/substitutions/__init__.py`:

```python
from .fastdds_profile import FastDDSProfile

__all__ = [
    "FastDDSProfile",
]
```

- [ ] **Step 6: Add `ng` to the top-level package**

In `launch_ext/__init__.py`, add `from . import ng` after `from . import events` and `"ng",` to `__all__`.

- [ ] **Step 7: Install the ng template**

In `setup.py`, add a second config entry to `data_files`, after the existing one:

```python
        ("share/" + package_name + "/config", glob.glob("launch_ext/config/*", recursive=True)),
        (
            "share/" + package_name + "/config/ng",
            glob.glob("launch_ext/ng/config/*", recursive=True),
        ),
```

The existing `launch_ext/config/*` glob is not recursive, so it will not pick the ng subdirectory up twice — but verify in Step 10 that only the two expected files land in the install tree.

- [ ] **Step 8: Move the two tests to ng and repoint their imports**

```bash
mkdir -p test/launch_ext/ng
git mv test/launch_ext/test_configure_middleware.py test/launch_ext/ng/test_configure_middleware.py
git mv test/launch_ext/test_fastdds_profile.py test/launch_ext/ng/test_fastdds_profile.py
```

In `test/launch_ext/ng/test_configure_middleware.py`, replace the three import lines:

```python
from launch_ext.ng.actions import ConfigureZenoh
from launch_ext.ng.discovery.configure_middleware import configure_middleware
from launch_ext.ng.discovery.middleware_config import (
    MiddlewareConfig,
    ZenohMiddleware,
    FastDDSMiddleware,
    MiddlewareTypes,
    FastDDSDiscoveryType,
)
```

In `test/launch_ext/ng/test_fastdds_profile.py`:

```python
from launch_ext.ng.substitutions import FastDDSProfile
from launch_ext.ng.discovery.middleware_config import IPEndPoint
```

No assertion in either file changes.

- [ ] **Step 9: Run the moved tests**

Run: `pixi run pytest test/launch_ext/ng -v`
Expected: every test that passed before the move passes now. A failure naming `launch_ext.ng` in a traceback means a relative import in Steps 2-4 was missed; a failure inside `FastDDSProfile.perform` about a missing template means the package has not been rebuilt — run `pixi run build` first, since `FindPackageShare` reads the install tree, not the source tree.

- [ ] **Step 10: Verify both templates install**

Run: `pixi run build && find install -path '*share/launch_ext/config*' -name '*.j2'`
Expected: exactly two paths — `.../share/launch_ext/config/fastdds_profile.xml.j2` and `.../share/launch_ext/config/ng/fastdds_profile.xml.j2`. They are byte-identical at this point; Task 2 makes them differ.

- [ ] **Step 11: Run the full suite**

Run: `pixi run test`
Expected: no new failures. The top-level 2.x modules are still in place and still exported, so nothing else moved.

- [ ] **Step 12: Commit**

```bash
git add launch_ext/ng launch_ext/__init__.py setup.py test/launch_ext/ng
git commit -m "feat: add the ng namespace carrying the 2.x middleware interface

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Restore the 1.27.0 interface at the top level

Checks the pre-2.0 middleware modules out of the tag, over the top of the 2.x copies that Task 1 duplicated into `ng`, and rewires the top-level export surfaces around them.

**Files:**
- Restore: `launch_ext/actions/configure_fastdds.py`, `launch_ext/actions/configure_fastdds_easy.py`, `launch_ext/actions/configure_zenoh.py`, `launch_ext/discovery/configure_middleware.py`, `launch_ext/discovery/discovery_config.py`, `launch_ext/substitutions/fastdds_superclient_environment.py`, `launch_ext/config/fastdds_profile.xml.j2`
- Delete: `launch_ext/discovery/middleware_config.py`, `launch_ext/substitutions/fastdds_profile.py`
- Modify: `launch_ext/actions/__init__.py`, `launch_ext/substitutions/__init__.py`, `launch_ext/substitutions/fastdds_client_environment.py`
- Test: `test/launch_ext/test_configure_middleware_legacy.py`

**Interfaces:**
- Consumes: `launch_ext.ng.*` from Task 1 — this task must not break it.
- Produces: `launch_ext.discovery.configure_middleware(discovery, with_server=True, then=None)`, `launch_ext.discovery.discovery_config.Discovery`, `launch_ext.actions.{ConfigureFastDDS, ConfigureFastDDSEasyMode, ConfigureZenoh}`, `launch_ext.substitutions.{FastDDSSuperclientEnvironment, get_fastdds_superclient_environment, FastDDSClientEnvironment}`.

- [ ] **Step 1: Write the failing smoke test**

Create `test/launch_ext/test_configure_middleware_legacy.py`:

```python
"""Tests for the restored pre-2.0 middleware interface."""

from launch.actions import ExecuteProcess, RegisterEventHandler, SetLaunchConfiguration
from launch.event_handlers import OnProcessExit

from launch_ext.actions import ConfigureFastDDS, ConfigureFastDDSEasyMode, ConfigureZenoh
from launch_ext.discovery import configure_middleware
from launch_ext.discovery.discovery_config import Discovery
from launch_ext.substitutions import (
    FastDDSClientEnvironment,
    FastDDSClientPath,
    FastDDSSuperclientEnvironment,
    get_fastdds_superclient_environment,
)


def test_zenoh_returns_super_client_reset_and_configure_zenoh():
    result = configure_middleware(Discovery(type="zenoh"))

    assert len(result) == 2
    assert isinstance(result[0], SetLaunchConfiguration)
    assert isinstance(result[1], ConfigureZenoh)


def test_zenoh_appends_then():
    then = SetLaunchConfiguration("my_flag", "1")
    result = configure_middleware(Discovery(type="zenoh"), then=then)

    assert len(result) == 3
    assert result[2] is then


def test_easy_returns_easy_mode_action():
    result = configure_middleware(Discovery(type="easy"))

    assert len(result) == 1
    assert isinstance(result[0], ConfigureFastDDSEasyMode)


def test_simple_returns_configure_fastdds():
    result = configure_middleware(Discovery(type="simple"))

    assert len(result) == 1
    assert isinstance(result[0], ConfigureFastDDS)


def test_fastdds_wraps_daemon_stop_and_shm_clean():
    result = configure_middleware(Discovery(type="fastdds"))

    # ExecuteAndAfterProcessExit is a function returning [process, RegisterEventHandler],
    # so the fastdds branch yields the daemon-stop process and its on-exit handler.
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], ExecuteProcess)
    assert isinstance(result[1], RegisterEventHandler)
    assert isinstance(result[1].event_handler, OnProcessExit)


def test_superclient_environment_sets_the_profile_env_var():
    env = get_fastdds_superclient_environment("fastdds")

    assert len(env) == 1
    value = next(iter(env.values()))
    assert isinstance(value, FastDDSSuperclientEnvironment)


def test_superclient_environment_is_empty_in_easy_mode():
    assert get_fastdds_superclient_environment("easy") == {}


def test_client_environment_alias_is_the_client_path_class():
    assert FastDDSClientEnvironment is FastDDSClientPath
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `pixi run pytest test/launch_ext/test_configure_middleware_legacy.py -v`
Expected: FAIL at collection — `ImportError: cannot import name 'ConfigureFastDDSEasyMode' from 'launch_ext.actions'`.

- [ ] **Step 3: Restore the files from the tag**

```bash
git checkout 1.27.0 -- \
  launch_ext/actions/configure_fastdds.py \
  launch_ext/actions/configure_fastdds_easy.py \
  launch_ext/actions/configure_zenoh.py \
  launch_ext/discovery/configure_middleware.py \
  launch_ext/discovery/discovery_config.py \
  launch_ext/substitutions/fastdds_superclient_environment.py \
  launch_ext/config/fastdds_profile.xml.j2
git rm launch_ext/discovery/middleware_config.py launch_ext/substitutions/fastdds_profile.py
```

Do not edit any restored file. If one of them turns out to need a change to work, stop and report it — it means the shared surface it depends on also moved, which this plan assumes it did not.

- [ ] **Step 4: Add the `FastDDSClientEnvironment` alias**

At the end of `launch_ext/substitutions/fastdds_client_environment.py`, after `get_fastdds_client_environment`:

```python
# The pre-2.0 name for FastDDSClientPath. The class is unchanged; only the name
# differed between the two generations, so both resolve to the same object.
FastDDSClientEnvironment = FastDDSClientPath
```

- [ ] **Step 5: Rewire `launch_ext/actions/__init__.py`**

Add the import back next to `from .configure_fastdds import ConfigureFastDDS`:

```python
from .configure_fastdds_easy import ConfigureFastDDSEasyMode
```

and `"ConfigureFastDDSEasyMode",` back into `__all__` after `"ConfigureFastDDS"`. Every other export in this file stays exactly as it is — the 2.x additions (`SubscribeRosTopic`, `ServeROSService`, `EmitEventOnTriggerService`, `Restartable`) are shared and must keep working.

- [ ] **Step 6: Rewire `launch_ext/substitutions/__init__.py`**

Replace the FastDDS import block with:

```python
from .fastdds_superclient_environment import (
    FastDDSSuperclientEnvironment,
    get_fastdds_superclient_environment,
)
from .fastdds_client_environment import (
    FastDDSClientEnvironment,
    FastDDSClientPath,
    get_fastdds_client_environment,
)
from .fastdds_env_var import FastDDSEnvVar, get_fastdds_default_profile_env_var
from .jinja_template import JinjaTemplate
from .ros_distro import ROSDistro
```

`FastDDSProfile` is gone from this file — it now lives in `launch_ext.ng.substitutions`. Update `__all__` to match: drop `"FastDDSProfile"`, add `"FastDDSSuperclientEnvironment"`, `"get_fastdds_superclient_environment"` and `"FastDDSClientEnvironment"`, keep `"FastDDSClientPath"`, `"JinjaTemplate"`, `"ROSDistro"` and the rest.

- [ ] **Step 7: Confirm `launch_ext/discovery/__init__.py` needs no change**

Run: `git diff 1.27.0 -- launch_ext/discovery/__init__.py`
Expected: empty. This file already matches the tag — it exports `configure_middleware` and nothing
else, and `Discovery` is imported from `launch_ext.discovery.discovery_config` exactly as it was at
`1.27.0`. If the diff is not empty, restore it with `git checkout 1.27.0 -- launch_ext/discovery/__init__.py`.

- [ ] **Step 8: Run the smoke test**

Run: `pixi run pytest test/launch_ext/test_configure_middleware_legacy.py -v`
Expected: PASS, all eight tests.

- [ ] **Step 9: Confirm ng still works**

Run: `pixi run build && pixi run pytest test/launch_ext/ng -v`
Expected: PASS. If `test_fastdds_profile.py` now fails on rendered XML content, the ng `FastDDSProfile` is reading the restored 1.27.0 template — recheck the `"ng"` path segment added in Task 1 Step 3.

- [ ] **Step 10: Run the full suite**

Run: `pixi run test`
Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git add -A launch_ext test/launch_ext/test_configure_middleware_legacy.py
git commit -m "feat: restore the pre-2.0 middleware interface at the top level

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Lock in coexistence, bump to 2.1.0, document

**Files:**
- Modify: `setup.py:9`, `package.xml:7`, `README.md`
- Test: `test/launch_ext/test_namespace_coexistence.py`

**Interfaces:**
- Consumes: everything Tasks 1 and 2 produced.
- Produces: nothing further.

- [ ] **Step 1: Write the failing coexistence test**

Create `test/launch_ext/test_namespace_coexistence.py`:

```python
"""Both middleware generations must import side by side and stay distinct."""

import inspect

from launch_ext.actions import ConfigureFastDDS as LegacyConfigureFastDDS
from launch_ext.discovery import configure_middleware as legacy_configure_middleware
from launch_ext.ng.actions import ConfigureFastDDS as NgConfigureFastDDS
from launch_ext.ng.discovery import configure_middleware as ng_configure_middleware


def test_configure_middleware_functions_are_distinct():
    assert legacy_configure_middleware is not ng_configure_middleware


def test_configure_fastdds_classes_are_distinct():
    assert LegacyConfigureFastDDS is not NgConfigureFastDDS


def test_legacy_configure_middleware_keeps_its_1_27_signature():
    params = inspect.signature(legacy_configure_middleware).parameters

    assert list(params) == ["discovery", "with_server", "then"]


def test_ng_configure_middleware_keeps_its_2_x_signature():
    params = inspect.signature(ng_configure_middleware).parameters

    assert list(params) == ["middleware_config", "inherit", "then"]


def test_legacy_configure_fastdds_keeps_its_1_27_signature():
    params = inspect.signature(LegacyConfigureFastDDS.__init__).parameters

    assert "with_discovery_server" in params
    assert "discovery_protocol" not in params


def test_ng_configure_fastdds_keeps_its_2_x_signature():
    params = inspect.signature(NgConfigureFastDDS.__init__).parameters

    assert "discovery_protocol" in params
    assert "with_discovery_server" not in params
```

- [ ] **Step 2: Run it**

Run: `pixi run pytest test/launch_ext/test_namespace_coexistence.py -v`
Expected: PASS on all six without any production change — Tasks 1 and 2 already put both generations in place. If a signature assertion fails, a restored or moved file was edited when it should have been copied verbatim; fix the file, not the test.

- [ ] **Step 3: Bump the version**

In `setup.py`, `version="2.0.0"` becomes `version="2.1.0"`. In `package.xml`, `<version>2.0.0</version>` becomes `<version>2.1.0</version>`.

- [ ] **Step 4: Document the two namespaces in `README.md`**

Replace the `#### ConfigureFastDDS` section (which documents a `config_file=` argument that no generation accepts) with:

```markdown
#### ConfigureFastDDS

Configure FastDDS middleware settings. Two generations of this interface ship
side by side:

- `launch_ext.actions.ConfigureFastDDS` — the pre-2.0 interface, taking
  `with_discovery_server`, `discovery_server_ip`, `allowed_interfaces` and
  `simple_discovery`. Paired with `launch_ext.discovery.configure_middleware`
  and the `Discovery` model in `launch_ext.discovery.discovery_config`.
- `launch_ext.ng.actions.ConfigureFastDDS` — the interface introduced in 2.0.0,
  taking `discovery_protocol`, `external_interfaces`, `local_discovery_server`,
  `domain_id` and `inherit`. Paired with
  `launch_ext.ng.discovery.configure_middleware` and `MiddlewareConfig`.

Pick one generation per launch file; they share no configuration types.

```python
from launch_ext.discovery import configure_middleware
from launch_ext.discovery.discovery_config import Discovery

configure_middleware(Discovery(type="fastdds"))
```

```python
from launch_ext.ng.discovery import configure_middleware
from launch_ext.ng.discovery import MiddlewareConfig, MiddlewareTypes

configure_middleware(MiddlewareConfig(middleware=MiddlewareTypes.FASTDDS))
```
```

- [ ] **Step 5: Run the full suite one last time**

Run: `pixi run test`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add test/launch_ext/test_namespace_coexistence.py setup.py package.xml README.md
git commit -m "feat: release the ng namespace alongside the restored interface as 2.1.0

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Follow-up, not in this plan

- Bumping gama's `<depend version_eq="1.27.0-*">launch_ext</depend>` (in `gama_bringup/package.xml:32` and `gama_gs_bringup/package.xml:13`) to `2.1.0-*`, which is what gives gama `JinjaTemplate`. Its middleware imports need no change.
- Tagging `2.1.0` and building the conda package.
