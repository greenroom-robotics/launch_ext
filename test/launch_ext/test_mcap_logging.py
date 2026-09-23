import json
import logging
import threading

import launch
import launch.actions
import launch.logging
import pytest
from mcap.exceptions import EndOfFile
from mcap.reader import NonSeekingReader, make_reader

from launch_ext.patches import mcap_logging


@pytest.fixture(autouse=True)
def clean_logging(tmp_path):
    """Fresh launch logging pointed at a temp dir; undo the patch afterwards."""
    launch.logging.reset()
    launch.logging.launch_config.log_dir = str(tmp_path)
    yield tmp_path
    mcap_logging._close_all()
    launch.logging.reset()


def read_messages(path):
    """Return [(topic, schema_name, decoded_json)] for every message in ``path``."""
    with open(path, "rb") as f:
        return [
            (channel.topic, schema.name, json.loads(message.data))
            for schema, channel, message in make_reader(f).iter_messages()
        ]


def run_launch(*actions):
    ls = launch.LaunchService()
    ls.include_launch_description(launch.LaunchDescription(list(actions)))
    assert ls.run() == 0


def test_launch_writes_mcap_instead_of_log_files(clean_logging):
    mcap_logging.apply()
    run_launch(
        launch.actions.ExecuteProcess(
            cmd=["sh", "-c", "echo hi; echo oops >&2"], name="talker", output="own_log"
        )
    )
    mcap_logging._close_all()

    msgs = read_messages(clean_logging / "launch.mcap")
    topics = {t for t, _, _ in msgs}
    # launch appends a counter to process names: talker-1, talker-2, ...
    (proc,) = {t.removesuffix("-stdout") for t in topics if t.endswith("-stdout")}
    assert proc.startswith("/talker-")
    assert {"/launch", proc, proc + "-stdout", proc + "-stderr"} <= topics
    assert {s for _, s, _ in msgs} == {"foxglove.Log"}
    stdout = [m for t, _, m in msgs if t == proc + "-stdout"]
    assert any("hi" in m["message"] for m in stdout)
    assert all(m["level"] == 2 for m in stdout)
    assert any("oops" in m["message"] for t, _, m in msgs if t == proc + "-stderr")
    assert list(clean_logging.glob("*.log")) == []

    with open(clean_logging / "launch.mcap", "rb") as f:
        (metadata,) = list(make_reader(f).iter_metadata())
    assert metadata.name == "launch"
    assert set(metadata.metadata) == {"hostname", "pid", "log_dir", "start_time"}


def test_record_fields_and_level_mapping(clean_logging):
    handler = mcap_logging.mcap_handler_factory(str(clean_logging / "unit.log"))
    logger = logging.getLogger("unit-test-logger")
    logger.addHandler(handler)
    logger.setLevel(1)
    for level in (5, logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL):
        logger.log(level, "lvl %d", level)
    mcap_logging._close_all()

    msgs = [m for t, _, m in read_messages(clean_logging / "launch.mcap")]
    assert [m["level"] for m in msgs] == [0, 1, 2, 3, 4, 5]
    first = msgs[0]
    assert first["message"] == "lvl 5"
    assert first["name"] == "unit-test-logger"
    assert first["file"].endswith("test_mcap_logging.py")
    assert first["line"] > 0
    assert 0 <= first["timestamp"]["nsec"] < 1_000_000_000


def test_readable_without_finish(clean_logging):
    """Simulates SIGKILL: every flushed record survives a missing footer."""
    handler = mcap_logging.mcap_handler_factory(str(clean_logging / "launch.log"))
    logger = logging.getLogger("crash-test")
    logger.addHandler(handler)
    logger.warning("before crash")
    sink = handler._sink
    sink._stream.close()  # no finish(): no summary, no footer
    sink._closed = True

    msgs = []
    with open(clean_logging / "launch.mcap", "rb") as f:
        try:
            # log_time_order=False streams; the default sorts (reads all) first.
            for _, _, m in NonSeekingReader(f).iter_messages(log_time_order=False):
                msgs.append(json.loads(m.data))
        except EndOfFile:
            pass  # expected: truncated file has no footer
    assert [m["message"] for m in msgs] == ["before crash"]


def test_unicode_output_round_trips(clean_logging):
    mcap_logging.apply()
    run_launch(
        launch.actions.ExecuteProcess(
            cmd=["sh", "-c", "printf 'héllo ✓ 日本\\n'"], name="uni", output="own_log"
        )
    )
    mcap_logging._close_all()
    msgs = read_messages(clean_logging / "launch.mcap")
    stdout = [m for t, _, m in msgs if t.startswith("/uni-") and t.endswith("-stdout")]
    assert any("héllo ✓ 日本" in m["message"] for m in stdout)


def test_separate_log_dirs_get_separate_files(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    ha = mcap_logging.mcap_handler_factory(str(a / "launch.log"))
    hb = mcap_logging.mcap_handler_factory(str(b / "launch.log"))
    logger = logging.getLogger("two-dirs")
    logger.addHandler(ha)
    logger.addHandler(hb)
    logger.warning("both")
    mcap_logging._close_all()
    for d in (a, b):
        assert [m["message"] for _, _, m in read_messages(d / "launch.mcap")] == ["both"]


def test_logging_after_close_is_dropped_quietly(clean_logging, capsys):
    handler = mcap_logging.mcap_handler_factory(str(clean_logging / "launch.log"))
    logger = logging.getLogger("late-logger")
    logger.addHandler(handler)
    mcap_logging._close_all()
    logger.warning("too late")  # must not raise or print a traceback
    assert "Traceback" not in capsys.readouterr().err
    assert read_messages(clean_logging / "launch.mcap") == []


def test_concurrent_emits_all_land(clean_logging):
    handler = mcap_logging.mcap_handler_factory(str(clean_logging / "launch.log"))
    logger = logging.getLogger("threads")
    logger.addHandler(handler)

    def spam(i):
        for j in range(200):
            logger.warning("t%d-%d", i, j)

    threads = [threading.Thread(target=spam, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    mcap_logging._close_all()
    assert len(read_messages(clean_logging / "launch.mcap")) == 8 * 200
