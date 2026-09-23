"""Write ``launch``'s log files into a single MCAP file instead of ``.log`` files.

Calling :func:`apply` swaps ``launch.logging.launch_config.log_handler_factory``
so every log file launch would open -- the main ``launch.log`` and each process's
``<proc>-stdout.log`` / ``<proc>-stderr.log`` / ``<proc>.log`` -- becomes a topic
(``/launch``, ``/<proc>-stdout``, ...) in ``<log_dir>/launch.mcap``. Records use
the ``foxglove.Log`` schema (JSON), so the file opens directly in Foxglove.

The file is unchunked and flushed after every record, so a killed launch loses
nothing already logged (the footer is missing; ``mcap recover`` rebuilds it).

Unlike ``relative_latest_symlink``, importing this module does *not* apply it:
it replaces the text logs, so it must be opted into. Either set
``LAUNCH_LOG_MCAP=1`` for ``ros2 launch`` (see
``launch_ext.ros2launch_options.mcap_logging``) or, in a custom entrypoint, call
:func:`apply` before constructing the ``LaunchService``::

    from launch_ext.patches import mcap_logging
    mcap_logging.apply()
"""

import atexit
import datetime
import json
import logging
import os
import socket
import threading

import launch.logging
from mcap.writer import CompressionType, Writer

# https://docs.foxglove.dev/docs/visualization/message-schemas/log
_FOXGLOVE_LOG_SCHEMA = {
    "title": "foxglove.Log",
    "description": "A log message",
    "type": "object",
    "properties": {
        "timestamp": {
            "type": "object",
            "title": "time",
            "properties": {
                "sec": {"type": "integer", "minimum": 0},
                "nsec": {"type": "integer", "minimum": 0, "maximum": 999999999},
            },
        },
        "level": {
            "title": "foxglove.LogLevel",
            "oneOf": [
                {"title": "UNKNOWN", "const": 0},
                {"title": "DEBUG", "const": 1},
                {"title": "INFO", "const": 2},
                {"title": "WARNING", "const": 3},
                {"title": "ERROR", "const": 4},
                {"title": "FATAL", "const": 5},
            ],
        },
        "message": {"type": "string"},
        "name": {"type": "string"},
        "file": {"type": "string"},
        "line": {"type": "integer", "minimum": 0},
    },
}

_LEVELS = (
    (logging.CRITICAL, 5),
    (logging.ERROR, 4),
    (logging.WARNING, 3),
    (logging.INFO, 2),
    (logging.DEBUG, 1),
)


_TRACEBACK_FORMATTER = logging.Formatter()


def _foxglove_level(levelno):
    """Map a stdlib ``logging`` level number to a ``foxglove.LogLevel`` value."""
    for threshold, level in _LEVELS:
        if levelno >= threshold:
            return level
    return 0


class _McapSink:
    """One MCAP file shared by every handler writing into the same log dir."""

    def __init__(self, path):
        self._lock = threading.Lock()
        self._closed = False
        self._channels = {}
        self._stream = open(path, "wb")
        self._writer = Writer(
            self._stream, use_chunking=False, compression=CompressionType.NONE
        )
        self._writer.start(library="launch_ext")
        self._schema_id = self._writer.register_schema(
            name="foxglove.Log",
            encoding="jsonschema",
            data=json.dumps(_FOXGLOVE_LOG_SCHEMA).encode(),
        )
        self._writer.add_metadata(
            "launch",
            {
                "hostname": socket.gethostname(),
                "pid": str(os.getpid()),
                "log_dir": os.path.dirname(path),
                "start_time": datetime.datetime.now().astimezone().isoformat(),
            },
        )
        self._stream.flush()

    def write(self, topic, log_time, data):
        with self._lock:
            if self._closed:
                return  # ponytail: records logged after shutdown are dropped
            channel_id = self._channels.get(topic)
            if channel_id is None:
                channel_id = self._writer.register_channel(
                    topic=topic, message_encoding="json", schema_id=self._schema_id
                )
                self._channels[topic] = channel_id
            self._writer.add_message(
                channel_id=channel_id, log_time=log_time, data=data, publish_time=log_time
            )
            self._stream.flush()

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._writer.finish()
            self._stream.close()


_sinks = {}
_sinks_lock = threading.Lock()


def _get_sink(log_dir):
    """Return the sink for ``log_dir``, opening its MCAP file on first use."""
    main_log = getattr(launch.logging.launch_config, "log_file_name", "launch.log")
    path = os.path.join(log_dir, main_log.removesuffix(".log") + ".mcap")
    with _sinks_lock:
        if path not in _sinks:
            _sinks[path] = _McapSink(path)
        return _sinks[path]


def _close_all():
    """Finish every open MCAP file. Runs at exit; tests call it directly."""
    with _sinks_lock:
        sinks = list(_sinks.values())
        _sinks.clear()
    for sink in sinks:
        sink.close()


atexit.register(_close_all)


# launch.logging.handlers.Handler is logging.Handler with launch's per-logger
# formatting trait (setFormatterFor), which launch calls on file handlers.
class McapLogHandler(launch.logging.handlers.Handler):
    """Write each log record as a ``foxglove.Log`` message on one MCAP topic."""

    def __init__(self, sink, topic):
        super().__init__()
        self._sink = sink
        self.topic = topic

    def emit(self, record):
        try:
            log_time = int(record.created * 1e9)
            sec, nsec = divmod(log_time, 1_000_000_000)
            # Keep tracebacks like FileHandler does; launch's text formatters are
            # ignored (fields carry timestamp/level/name), so format them directly.
            message = record.getMessage()
            if record.exc_info:
                message += "\n" + _TRACEBACK_FORMATTER.formatException(record.exc_info)
            if record.stack_info:
                message += "\n" + _TRACEBACK_FORMATTER.formatStack(record.stack_info)
            data = json.dumps(
                {
                    "timestamp": {"sec": sec, "nsec": nsec},
                    "level": _foxglove_level(record.levelno),
                    "name": record.name,
                    "message": message,
                    "file": record.pathname,
                    "line": record.lineno,
                }
            ).encode()
            self._sink.write(self.topic, log_time, data)
        except Exception:
            self.handleError(record)


def mcap_handler_factory(file_path, encoding=None):
    """``log_handler_factory`` replacement: ``<dir>/<name>.log`` -> topic ``/<name>``."""
    log_dir, file_name = os.path.split(file_path)
    return McapLogHandler(_get_sink(log_dir), "/" + file_name.removesuffix(".log"))


def apply():
    """Route all launch log files into MCAP (idempotent)."""
    launch.logging.launch_config.log_handler_factory = mcap_handler_factory
