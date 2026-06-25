"""End-to-end test for Restartable against a live LaunchService.

A real launch run spawns a generation-0 process; we emit a Restart event with a
new payload and assert that the old process is actually killed and a fresh
process is started with the new argument. The LaunchService runs on the main
thread; a driver thread sequences the restart and a watchdog guarantees exit.
"""

import os
import threading
import time
from pathlib import Path

from launch import LaunchDescription, LaunchService
from launch.actions import ExecuteProcess

from launch_ext.actions import Restartable
from launch_ext.events import Restart


def _wait_for_pid_file(path: Path, timeout: float) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists():
            text = path.read_text().strip()
            if text:
                return int(text)
        time.sleep(0.05)
    raise TimeoutError(f"{path} was not written within {timeout}s")


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _wait_until_dead(pid: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _is_alive(pid):
            return True
        time.sleep(0.05)
    return False


def test_restartable_action_kills_old_and_starts_new_with_payload(tmp_path):
    results = {}

    def factory(context, restart_event):
        gen = restart_event.payload["gen"] if restart_event is not None else 0
        pid_file = tmp_path / f"gen_{gen}.pid"
        # Write our pid so the test can track this exact process, then idle.
        # Exit 0 on SIGINT (launch's shutdown signal) so teardown is clean.
        code = (
            "import os, signal, sys, time\n"
            "signal.signal(signal.SIGINT, lambda *a: sys.exit(0))\n"
            f"open(r'{pid_file}', 'w').write(str(os.getpid()))\n"
            "time.sleep(300)\n"
        )
        return [ExecuteProcess(cmd=["python3", "-u", "-c", code])]

    stack = Restartable(factory=factory)
    ls = LaunchService()
    ls.include_launch_description(LaunchDescription([stack]))

    def driver():
        try:
            pid0 = _wait_for_pid_file(tmp_path / "gen_0.pid", timeout=20)
            results["pid0"] = pid0

            # Trigger a restart with a new payload (as the bridge node would).
            ls.emit_event(Restart(action=stack, gen=1))

            pid1 = _wait_for_pid_file(tmp_path / "gen_1.pid", timeout=20)
            results["pid1"] = pid1

            results["pid0_died"] = _wait_until_dead(pid0, timeout=10)
            results["pid1_alive"] = _is_alive(pid1)
        except Exception as exc:  # noqa: BLE001 - surfaced via assert below
            results["error"] = repr(exc)
        finally:
            ls.shutdown()

    driver_thread = threading.Thread(target=driver, daemon=True)
    watchdog = threading.Thread(target=lambda: (time.sleep(50), ls.shutdown()), daemon=True)
    driver_thread.start()
    watchdog.start()

    ls.run()
    driver_thread.join(timeout=10)

    assert "error" not in results, results.get("error")
    assert results["pid0"] != results["pid1"], "restart reused the same process"
    assert results["pid0_died"], "the original generation was not torn down"
    assert results["pid1_alive"], "the new generation was not running"
