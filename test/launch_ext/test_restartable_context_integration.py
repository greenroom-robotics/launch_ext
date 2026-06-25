"""Characterization tests: what happens to the LaunchContext across a restart.

A Restartable does not scope its generations in a GroupAction, so every
generation runs against the *same* LaunchContext. These tests launch one or more
generations and snapshot the context as seen during each generation's
visitation (via an OpaqueFunction that runs after the generation's other
entities). They document the observable consequences:

* the context object is reused (not recreated) between launches;
* launch configurations set by a generation persist and are overwritten by the
  next generation (last-write-wins, no scoping);
* the Restartable's own OnRestart handler is registered once, not per generation;
* with pruning enabled (the default), a dead generation's event handlers are
  removed, so the handler count stays bounded across many restarts.

Each generation's process writes a "ready" file once it has installed its SIGINT
handler; the driver waits for that file before triggering the next restart, so
teardown is a clean SIGINT (no signal races) and the run output stays quiet.
"""

import threading
import time
from pathlib import Path

from launch import LaunchDescription, LaunchService
from launch.actions import ExecuteProcess, OpaqueFunction, SetLaunchConfiguration

from launch_ext.actions import Restartable
from launch_ext.event_handlers import OnRestart

# Writes a readiness file (proving its SIGINT handler is installed) then idles;
# exits 0 on SIGINT so teardown is clean.
_READY_THEN_SLEEP = (
    "import os, signal, sys, time\n"
    "signal.signal(signal.SIGINT, lambda *a: sys.exit(0))\n"
    "open(sys.argv[1], 'w').write(str(os.getpid()))\n"
    "time.sleep(300)\n"
)


def _wait_for_file(path: Path, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists():
            return True
        time.sleep(0.05)
    return False


def _run_generations(tmp_path: Path, num_generations: int, *, prune: bool = True) -> list:
    """Launch ``num_generations`` generations (gen 0 + restarts), returning per-gen snapshots."""
    captures = []

    def factory(context, restart_event):
        gen = restart_event.payload["gen"] if restart_event is not None else 0
        ready_file = tmp_path / f"ready_{gen}"

        def capture(ctx):
            captures.append(
                {
                    "gen": gen,
                    "context_id": id(ctx),
                    "generation_config": ctx.launch_configurations.get("generation"),
                    "num_event_handlers": len(ctx._event_handlers),
                    "num_on_restart": sum(
                        1 for h in ctx._event_handlers if isinstance(h, OnRestart)
                    ),
                }
            )
            return None

        return [
            SetLaunchConfiguration("generation", str(gen)),
            ExecuteProcess(cmd=["python3", "-u", "-c", _READY_THEN_SLEEP, str(ready_file)]),
            OpaqueFunction(function=capture),
        ]

    stack = Restartable(factory=factory, prune_event_handlers=prune)
    ls = LaunchService()
    ls.include_launch_description(LaunchDescription([stack]))

    results = {}

    def driver():
        try:
            for gen in range(num_generations):
                if not _wait_for_file(tmp_path / f"ready_{gen}", timeout=20):
                    results["timed_out_on"] = gen
                    return
                if gen + 1 < num_generations:
                    stack.request_restart(gen=gen + 1)  # uses the stored context
            results["ok"] = True
        finally:
            ls.shutdown()

    driver_thread = threading.Thread(target=driver, daemon=True)
    watchdog = threading.Thread(target=lambda: (time.sleep(60), ls.shutdown()), daemon=True)
    driver_thread.start()
    watchdog.start()

    ls.run()
    driver_thread.join(timeout=10)

    assert results.get("ok"), results
    assert len(captures) == num_generations
    return captures


def test_restart_reuses_the_same_launch_context(tmp_path):
    gen0, gen1 = _run_generations(tmp_path, 2)
    assert gen0["context_id"] == gen1["context_id"]


def test_restart_reapplies_configuration_in_the_shared_context(tmp_path):
    gen0, gen1 = _run_generations(tmp_path, 2)
    # Not scoped: each generation sets the value, the relaunch overwrites it, and
    # it persists on the shared context (last-write-wins).
    assert gen0["generation_config"] == "0"
    assert gen1["generation_config"] == "1"


def test_restart_does_not_duplicate_the_on_restart_handler(tmp_path):
    gen0, gen1 = _run_generations(tmp_path, 2)
    # execute() runs once for the Restartable, so its handler is registered once.
    assert gen0["num_on_restart"] == 1
    assert gen1["num_on_restart"] == 1


def test_dead_generation_event_handlers_are_pruned(tmp_path):
    gen0, gen1 = _run_generations(tmp_path, 2)
    # With pruning (the default), the first generation's handlers are removed on
    # teardown, so the second generation sees the same count, not an accumulated one.
    assert gen1["num_event_handlers"] == gen0["num_event_handlers"]


def test_event_handlers_do_not_grow_across_many_restarts(tmp_path):
    captures = _run_generations(tmp_path, 4)
    counts = [c["num_event_handlers"] for c in captures]
    # Every generation registers the same number of handlers; pruning keeps the
    # total from growing as restarts accumulate.
    assert len(set(counts)) == 1, counts


def test_without_pruning_event_handlers_accumulate(tmp_path):
    captures = _run_generations(tmp_path, 3, prune=False)
    counts = [c["num_event_handlers"] for c in captures]
    # Opting out restores the raw launch behaviour: handlers from dead
    # generations linger, so the count strictly grows.
    assert counts[0] < counts[1] < counts[2], counts
