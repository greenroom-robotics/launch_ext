# Copyright 2018 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module for the ExecuteLocalExt action."""

import asyncio
import io
import logging
import os
import platform
import signal
import traceback
from typing import Any  # noqa: F401
from typing import Callable
from typing import cast
from typing import Dict
from typing import List
from typing import Optional
from typing import Text
from typing import Tuple  # noqa: F401
from typing import Union

import launch.logging

from osrf_pycommon.process_utils import async_execute_process  # type: ignore
from osrf_pycommon.process_utils import AsyncSubprocessProtocol

from launch.actions.emit_event import EmitEvent
from launch.actions.opaque_function import OpaqueFunction
from launch.actions.timer_action import TimerAction

from launch.action import Action
from launch.conditions import evaluate_condition_expression
from launch.descriptions import Executable
from launch.event import Event
from launch.event_handler import EventHandler
from launch.event_handlers import OnProcessExit
from launch.event_handlers import OnProcessIO
from launch.event_handlers import OnProcessStart
from launch.event_handlers import OnShutdown
from launch.events import matches_action
from launch.events import Shutdown

# from launch.events.process import ProcessExited
# from launch.events.process import ProcessIO
from launch.events.process import ProcessStarted
from launch.events.process import ProcessStderr
from launch.events.process import ProcessStdin
from launch.events.process import ProcessStdout
from launch.events.process import ShutdownProcess
from launch.events.process import SignalProcess
from launch.launch_context import LaunchContext
from launch.launch_description import LaunchDescription
from launch.launch_description_entity import LaunchDescriptionEntity
from launch.some_entities_type import SomeEntitiesType
from launch.some_substitutions_type import SomeSubstitutionsType
from launch.substitution import Substitution  # noqa: F401
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PythonExpression
from launch.utilities import is_a_subclass
from launch.utilities import normalize_to_list_of_substitutions
from launch.utilities import perform_substitutions
from launch.utilities.type_utils import normalize_typed_substitution
from launch.utilities.type_utils import perform_typed_substitution

# we have to include the ProcessIO and ProcessExited events here
# because they hardcore the type of action

# Copyright 2018-2021 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module for OnProcessIO class."""

from typing import Callable
from typing import cast
from typing import Optional
from typing import TYPE_CHECKING
from typing import Union

from launch.event_handlers.on_action_event_base import OnActionEventBase
from launch.event import Event
from launch.events.process import ProcessIO
from launch.launch_context import LaunchContext
from launch.some_entities_type import SomeEntitiesType


class OnProcessIO(OnActionEventBase):
    """Convenience class for handling I/O from processes via events."""

    # TODO(wjwwood): make the __init__ more flexible like OnProcessExit, so
    # that it can take SomeEntitiesType directly or a callable that returns it.
    def __init__(
        self,
        *,
        target_action: Optional[Union[Callable[["Action"], bool], "Action"]] = None,
        on_stdin: Optional[Callable[[ProcessIO], Optional[SomeEntitiesType]]] = None,
        on_stdout: Optional[Callable[[ProcessIO], Optional[SomeEntitiesType]]] = None,
        on_stderr: Optional[Callable[[ProcessIO], Optional[SomeEntitiesType]]] = None,
        **kwargs,
    ) -> None:
        """Create an OnProcessIO event handler."""

        def handle(event: Event, _: LaunchContext) -> Optional[SomeEntitiesType]:
            event = cast(ProcessIO, event)
            if event.from_stdout and on_stdout is not None:
                return on_stdout(event)
            elif event.from_stderr and on_stderr is not None:
                return on_stderr(event)
            elif event.from_stdin and on_stdin is not None:
                return on_stdin(event)
            return None

        super().__init__(
            action_matcher=target_action,
            on_event=handle,
            target_event_cls=ProcessIO,
            target_action_cls=ExecuteLocalExt,
            **kwargs,
        )


# Copyright 2018-2021 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module for OnProcessExit class."""

from launch.events.process import ProcessExited


class OnProcessExit(OnActionEventBase):
    """
    Convenience class for handling a process exited event.

    It may be configured to only handle the exiting of a specific action,
    or to handle all exited processes.
    """

    def __init__(
        self,
        *,
        target_action: Optional[
            Union[Callable[["ExecuteLocalExt"], bool], "ExecuteLocalExt"]
        ] = None,
        on_exit: Union[
            SomeEntitiesType, Callable[[ProcessExited, LaunchContext], Optional[SomeEntitiesType]]
        ],
        **kwargs,
    ) -> None:
        """Create an OnProcessExit event handler."""
        super().__init__(
            action_matcher=cast(
                Optional[Union[Callable[["Action"], bool], "Action"]], target_action
            ),
            on_event=cast(
                Union[
                    SomeEntitiesType, Callable[[Event, LaunchContext], Optional[SomeEntitiesType]]
                ],
                on_exit,
            ),
            target_event_cls=ProcessExited,
            target_action_cls=ExecuteLocalExt,
            **kwargs,
        )


from typing import Set

from pathlib import Path
import psutil


def get_inodes(pid: int) -> Set[int]:
    fds_to_check = [0, 1, 2]
    inodes = set()

    for fd in fds_to_check:
        try:
            fdinfo = Path(f"/proc/{pid}/fdinfo/{fd}").read_text().strip().split("\n")
            fdinfo = [s.split(":\t") for s in fdinfo]
            fdinfo = {s[0]: int(s[1]) for s in fdinfo}

            inodes.add(fdinfo["ino"])
        except FileNotFoundError as e:
            continue
        except PermissionError as e:
            continue
        except IndexError as e:
            continue

    return inodes


def get_pids_with_inodes(inodes: Set[int]) -> Set[int]:
    pids = set()

    for pid in psutil.pids():
        if inodes & get_inodes(pid):
            pids.add(pid)

    return pids


class ExecuteLocalExt(Action):
    """Action that begins executing a process on the local system and sets up event handlers."""

    def __init__(
        self,
        *,
        process_description: Executable,
        shell: bool = False,
        sigterm_timeout: SomeSubstitutionsType = LaunchConfiguration("sigterm_timeout", default=5),
        sigkill_timeout: SomeSubstitutionsType = LaunchConfiguration("sigkill_timeout", default=5),
        emulate_tty: bool = False,
        output: SomeSubstitutionsType = "log",
        output_format: str = "[{this.process_description.final_name}] {line}",
        cached_output: bool = False,
        log_cmd: bool = False,
        on_exit: Optional[
            Union[
                SomeEntitiesType,
                Callable[[ProcessExited, LaunchContext], Optional[SomeEntitiesType]],
            ]
        ] = None,
        respawn: Union[bool, SomeSubstitutionsType] = False,
        respawn_delay: Optional[float] = None,
        respawn_max_retries: int = -1,
        wait_on_child_processes: bool = False,
        **kwargs,
    ) -> None:
        """
        Construct an ExecuteLocalExt action.

        Many arguments are passed eventually to :class:`subprocess.Popen`, so
        see the documentation for the class for additional details.

        This action, once executed, registers several event handlers for
        various process related events and will also emit events asynchronously
        when certain events related to the process occur.

        Handled events include:

        - launch.events.process.ShutdownProcess:

          - begins standard shutdown procedure for a running executable

        - launch.events.process.SignalProcess:

          - passes the signal provided by the event to the running process

        - launch.events.process.ProcessStdin:

          - passes the text provided by the event to the stdin of the process

        - launch.events.Shutdown:

          - same as ShutdownProcess

        Emitted events include:

        - launch.events.process.ProcessStarted:

            - emitted when the process starts

        - launch.events.process.ProcessExited:

            - emitted when the process exits
            - event contains return code

        - launch.events.process.ProcessStdout and launch.events.process.ProcessStderr:

            - emitted when the process produces data on either the stdout or stderr pipes
            - event contains the data from the pipe

        Note that output is just stored in this class and has to be properly
        implemented by the event handlers for the process's ProcessIO events.

        :param: process_description the `launch.descriptions.Executable` to execute
            as a local process
        :param: shell if True, a shell is used to execute the cmd
        :param: sigterm_timeout time until shutdown should escalate to SIGTERM,
            as a string or a list of strings and Substitutions to be resolved
            at runtime, defaults to the LaunchConfiguration called
            'sigterm_timeout'
        :param: sigkill_timeout time until escalating to SIGKILL after SIGTERM,
            as a string or a list of strings and Substitutions to be resolved
            at runtime, defaults to the LaunchConfiguration called
            'sigkill_timeout'
        :param: emulate_tty emulate a tty (terminal), defaults to False, but can
            be overridden with the LaunchConfiguration called 'emulate_tty',
            the value of which is evaluated as true or false according to
            :py:func:`evaluate_condition_expression`.
            Throws :py:exc:`InvalidConditionExpressionError` if the
            'emulate_tty' configuration does not represent a boolean.
        :param: output configuration for process output logging. Defaults to 'log'
            i.e. log both stdout and stderr to launch main log file and stderr to
            the screen.
            Overridden externally by the OVERRIDE_LAUNCH_PROCESS_OUTPUT envvar value.
            See `launch.logging.get_output_loggers()` documentation for further
            reference on all available options.
        :param: output_format for logging each output line, supporting `str.format()`
            substitutions with the following keys in scope: `line` to reference the raw
            output line and `this` to reference this action instance.
        :param: log_cmd if True, prints the final cmd before executing the
            process, which is useful for debugging when substitutions are
            involved.
        :param: cached_output if `True`, both stdout and stderr will be cached.
            Use get_stdout() and get_stderr() to read the buffered output.
        :param: on_exit list of actions to execute upon process exit.
        :param: respawn if 'True', relaunch the process that abnormally died.
            Either a boolean or a Substitution to be resolved at runtime. Defaults to 'False'.
        :param: respawn_delay a delay time to relaunch the died process if respawn is 'True'.
        :param: respawn_max_retries number of times to respawn the process if respawn is 'True'.
                A negative value will respawn an infinite number of times (default behavior).
        """
        super().__init__(**kwargs)
        self.__process_description = process_description
        self.__shell = shell
        self.__sigterm_timeout = normalize_to_list_of_substitutions(sigterm_timeout)
        self.__sigkill_timeout = normalize_to_list_of_substitutions(sigkill_timeout)
        self.__emulate_tty = emulate_tty
        # Note: we need to use a temporary here so that we don't assign values with different types
        # to the same variable
        tmp_output: SomeSubstitutionsType = os.environ.get(
            "OVERRIDE_LAUNCH_PROCESS_OUTPUT", output
        )
        self.__output: Union[dict, List[Substitution]]
        if not isinstance(tmp_output, dict):
            self.__output = normalize_to_list_of_substitutions(tmp_output)
        else:
            self.__output = tmp_output
        self.__output_format = output_format

        self.__log_cmd = log_cmd
        self.__cached_output = cached_output
        self.__on_exit = on_exit
        self.__respawn = normalize_typed_substitution(respawn, bool)
        self.__respawn_delay = respawn_delay

        self.__wait_for_child_pids = wait_on_child_processes

        self.__respawn_max_retries = respawn_max_retries
        self.__respawn_retries = 0

        self.__process_event_args = None  # type: Optional[Dict[Text, Any]]
        self._subprocess_protocol = None  # type: Optional[Any]
        self._subprocess_transport = None
        self.__completed_future = None  # type: Optional[asyncio.Future]
        self.__shutdown_future = None  # type: Optional[asyncio.Future]
        self.__sigterm_timer = None  # type: Optional[TimerAction]
        self.__sigkill_timer = None  # type: Optional[TimerAction]
        self.__stdout_buffer = io.StringIO()
        self.__stderr_buffer = io.StringIO()

        self.__executed = False

    @property
    def process_description(self):
        """Getter for process_description."""
        return self.__process_description

    @property
    def shell(self):
        """Getter for shell."""
        return self.__shell

    @property
    def emulate_tty(self):
        """Getter for emulate_tty."""
        return self.__emulate_tty

    @property
    def sigkill_timeout(self):
        """Getter for sigkill timeout."""
        return self.__sigkill_timeout

    @property
    def sigterm_timeout(self):
        """Getter for sigterm timeout."""
        return self.__sigterm_timeout

    @property
    def output(self):
        """Getter for output."""
        return self.__output

    @property
    def process_details(self):
        """Getter for the process details, e.g. name, pid, cmd, etc., or None if not started."""
        return self.__process_event_args

    def get_sub_entities(self):
        if isinstance(self.__on_exit, list):
            return self.__on_exit
        return []

    def _shutdown_process(self, context, *, send_sigint):
        if self.__shutdown_future is None or self.__shutdown_future.done():
            # Execution not started or already done, nothing to do.
            return None

        if self.__completed_future is None:
            # Execution not started so nothing to do, but self.__shutdown_future should prevent
            # execution from starting in the future.
            self.__shutdown_future.set_result(None)
            return None
        if self.__completed_future.done():
            # If already done, then nothing to do.
            self.__shutdown_future.set_result(None)
            return None

        # Defer shut down if the process is scheduled to be started
        if self.process_details is None or self._subprocess_transport is None:
            # Do not set shutdown result, as event is postponed
            context.register_event_handler(
                OnProcessStart(
                    on_start=lambda event, context: self._shutdown_process(
                        context, send_sigint=send_sigint
                    )
                )
            )
            return None

        self.__shutdown_future.set_result(None)

        # Otherwise process is still running, start the shutdown procedures.
        context.extend_locals({"process_name": self.process_details["name"]})
        actions_to_return = self.__get_shutdown_timer_actions()
        if send_sigint:
            actions_to_return.append(self.__get_sigint_event())
        return actions_to_return

    def __on_shutdown_process_event(self, context: LaunchContext) -> Optional[LaunchDescription]:
        typed_event = cast(ShutdownProcess, context.locals.event)
        if not typed_event.process_matcher(self):
            # this event whas not intended for this process
            return None
        return self._shutdown_process(context, send_sigint=True)

    def __on_signal_process_event(self, context: LaunchContext) -> Optional[LaunchDescription]:
        typed_event = cast(SignalProcess, context.locals.event)
        if not typed_event.process_matcher(self):
            # this event whas not intended for this process
            return None
        if self.process_details is None:
            raise RuntimeError("Signal event received before execution.")
        if self._subprocess_transport is None:
            raise RuntimeError("Signal event received before subprocess transport available.")
        if self._subprocess_protocol.complete.done():
            # the process is done or is cleaning up, no need to signal
            self.__logger.debug(
                "signal '{}' not set to '{}' because it is already closing".format(
                    typed_event.signal_name, self.process_details["name"]
                ),
            )
            return None
        if platform.system() == "Windows" and typed_event.signal_name == "SIGINT":
            # TODO(wjwwood): remove this when/if SIGINT is fixed on Windows
            self.__logger.warning(
                "'SIGINT' sent to process[{}] not supported on Windows, escalating to 'SIGTERM'".format(
                    self.process_details["name"]
                ),
            )
            typed_event = SignalProcess(
                signal_number=signal.SIGTERM, process_matcher=lambda process: True
            )
        self.__logger.info(
            "sending signal '{}' to process[{}]".format(
                typed_event.signal_name, self.process_details["name"]
            )
        )
        try:
            if typed_event.signal_name == "SIGKILL":
                self._subprocess_transport.kill()  # works on both Windows and POSIX
                return None
            self._subprocess_transport.send_signal(typed_event.signal)
            return None
        except ProcessLookupError:
            self.__logger.debug(
                "signal '{}' not sent to '{}' because it has closed already".format(
                    typed_event.signal_name, self.process_details["name"]
                )
            )

    def __on_process_stdin(self, event: ProcessIO) -> Optional[SomeEntitiesType]:
        self.__logger.warning(
            f"in ExecuteProcess('{id(self)}').__on_process_stdin_event()",
        )
        cast(ProcessStdin, event)
        return None

    def __on_process_output(
        self, event: ProcessIO, buffer: io.TextIOBase, logger: logging.Logger
    ) -> None:
        to_write = event.text.decode(errors="replace")
        if buffer.closed:
            # buffer was probably closed by __flush_buffers on shutdown.  Output without
            # buffering.
            logger.info(self.__output_format.format(line=to_write, this=self))
        else:
            buffer.write(to_write)
            buffer.seek(0)
            last_line = None
            for line in buffer:
                if line.endswith(os.linesep):
                    logger.info(
                        self.__output_format.format(line=line[: -len(os.linesep)], this=self)
                    )
                else:
                    last_line = line
                    break
            buffer.seek(0)
            buffer.truncate(0)
            if last_line is not None:
                buffer.write(last_line)

    def __flush_buffers(self, event, context):
        line = self.__stdout_buffer.getvalue()
        if line != "":
            self.__stdout_logger.info(self.__output_format.format(line=line, this=self))

        line = self.__stderr_buffer.getvalue()
        if line != "":
            self.__stderr_logger.info(self.__output_format.format(line=line, this=self))

        # the respawned process needs to reuse these StringIO resources,
        # close them only after receiving the shutdown
        if self.__shutdown_future is None or self.__shutdown_future.done():
            self.__stdout_buffer.close()
            self.__stderr_buffer.close()
        else:
            self.__stdout_buffer.seek(0)
            self.__stdout_buffer.truncate(0)
            self.__stderr_buffer.seek(0)
            self.__stderr_buffer.truncate(0)

    def __on_process_output_cached(self, event: ProcessIO, buffer, logger) -> None:
        to_write = event.text.decode(errors="replace")
        last_cursor = buffer.tell()
        buffer.seek(0, os.SEEK_END)  # go to end of buffer
        buffer.write(to_write)
        buffer.seek(last_cursor)
        new_cursor = last_cursor
        for line in buffer:
            if not line.endswith(os.linesep):
                break
            new_cursor = buffer.tell()
            logger.info(self.__output_format.format(line=line[: -len(os.linesep)], this=self))
        buffer.seek(new_cursor)

    def __flush_cached_buffers(self, event, context):
        for line in self.__stdout_buffer:
            self.__stdout_logger.info(self.__output_format.format(line=line, this=self))

        for line in self.__stderr_buffer:
            self.__stderr_logger.info(self.__output_format.format(line=line, this=self))

    def __on_shutdown(self, event: Event, context: LaunchContext) -> Optional[SomeEntitiesType]:
        due_to_sigint = cast(Shutdown, event).due_to_sigint
        return self._shutdown_process(
            context,
            send_sigint=not due_to_sigint or context.noninteractive,
        )

    def __get_shutdown_timer_actions(self) -> List[Action]:
        base_msg = (
            "process[{}] failed to terminate '{}' seconds after receiving '{}', escalating to '{}'"
        )

        def printer(context, msg, timeout_substitutions):
            self.__logger.error(
                msg.format(
                    context.locals.process_name,
                    perform_substitutions(context, timeout_substitutions),
                )
            )

        sigterm_timeout = self.__sigterm_timeout
        sigkill_timeout = [
            PythonExpression(
                ("float(", *self.__sigterm_timeout, ") + float(", *self.__sigkill_timeout, ")")
            )
        ]
        # Setup a timer to send us a SIGTERM if we don't shutdown quickly.
        self.__sigterm_timer = TimerAction(
            period=sigterm_timeout,
            actions=[
                OpaqueFunction(
                    function=printer,
                    args=(base_msg.format("{}", "{}", "SIGINT", "SIGTERM"), sigterm_timeout),
                ),
                EmitEvent(
                    event=SignalProcess(
                        signal_number=signal.SIGTERM, process_matcher=matches_action(self)
                    )
                ),
            ],
            cancel_on_shutdown=False,
        )
        # Setup a timer to send us a SIGKILL if we don't shutdown after SIGTERM.
        self.__sigkill_timer = TimerAction(
            period=sigkill_timeout,
            actions=[
                OpaqueFunction(
                    function=printer,
                    args=(base_msg.format("{}", "{}", "SIGTERM", "SIGKILL"), sigkill_timeout),
                ),
                EmitEvent(
                    event=SignalProcess(
                        signal_number="SIGKILL", process_matcher=matches_action(self)
                    )
                ),
            ],
            cancel_on_shutdown=False,
        )
        return [
            cast(Action, self.__sigterm_timer),
            cast(Action, self.__sigkill_timer),
        ]

    def __get_sigint_event(self):
        return EmitEvent(
            event=SignalProcess(
                signal_number=signal.SIGINT,
                process_matcher=matches_action(self),
            )
        )

    def __cleanup(self):
        # Cancel any pending timers we started.
        if self.__sigterm_timer is not None:
            self.__sigterm_timer.cancel()
        if self.__sigkill_timer is not None:
            self.__sigkill_timer.cancel()
        # Close subprocess transport if any.
        if self._subprocess_transport is not None:
            self._subprocess_transport.close()
        # Signal that we're done to the launch system.
        self.__completed_future.set_result(None)

    class __ProcessProtocol(AsyncSubprocessProtocol):
        def __init__(
            self,
            action: "ExecuteLocalExt",
            context: LaunchContext,
            process_event_args: Dict,
            **kwargs,
        ) -> None:
            super().__init__(**kwargs)
            self.__context = context
            self.__process_event_args = process_event_args
            self.__logger = launch.logging.get_logger(process_event_args["name"])

        def connection_made(self, transport):
            self.__logger.info(
                f"process started with pid [{transport.get_pid()}]",
            )
            super().connection_made(transport)
            self.__process_event_args["pid"] = transport.get_pid()

        def on_stdout_received(self, data: bytes) -> None:
            self.__context.emit_event_sync(ProcessStdout(text=data, **self.__process_event_args))

        def on_stderr_received(self, data: bytes) -> None:
            self.__context.emit_event_sync(ProcessStderr(text=data, **self.__process_event_args))

    async def _wait_for_inodes_to_expire(self, fd_inodes: Set[int]) -> Set[int]:
        pids = set()
        while True:
            child_pids = get_pids_with_inodes(fd_inodes)

            if len(child_pids) == 0:
                break

            pids.update(child_pids)
            self.__logger.debug(
                "process has child processes with PIDs: {}".format(
                    ", ".join(map(str, child_pids)),
                )
            )

            await asyncio.sleep(0.25)

        return pids

    async def __execute_process(self, context: LaunchContext) -> None:
        process_event_args = self.__process_event_args
        if process_event_args is None:
            raise RuntimeError("process_event_args unexpectedly None")

        cmd = process_event_args["cmd"]
        cwd = process_event_args["cwd"]
        env = process_event_args["env"]
        if self.__log_cmd:
            self.__logger.info(
                "process details: cmd='{}', cwd='{}', custom_env?={}".format(
                    " ".join(filter(lambda part: part.strip(), cmd)),
                    cwd,
                    "True" if env is not None else "False",
                )
            )

        emulate_tty = self.__emulate_tty
        if "emulate_tty" in context.launch_configurations:
            emulate_tty = evaluate_condition_expression(
                context,
                normalize_to_list_of_substitutions(context.launch_configurations["emulate_tty"]),
            )

        try:
            transport, self._subprocess_protocol = await async_execute_process(
                lambda **kwargs: self.__ProcessProtocol(
                    self, context, process_event_args, **kwargs
                ),
                cmd=cmd,
                cwd=cwd,
                env=env,
                shell=self.__shell,
                emulate_tty=emulate_tty,
                stderr_to_stdout=False,
            )
        except Exception:
            self.__logger.error(
                f"exception occurred while executing process:\n{traceback.format_exc()}"
            )
            self.__cleanup()
            return

        pid = transport.get_pid()
        self._subprocess_transport = transport

        # get inode[s] for stdout and stderr for the PID
        fd_inodes = get_inodes(pid)
        self.__logger.debug(f"pid has stdout/stderr inodes: {fd_inodes}")

        await context.emit_event(ProcessStarted(**process_event_args))

        returncode = await self._subprocess_protocol.complete

        if self.__wait_for_child_pids:
            self.__logger.info("waiting for child processes with parent's stdin/stdout pipes.")
            child_pids = await self._wait_for_inodes_to_expire(fd_inodes)
            self.__logger.info(
                "child processes [pids {}] have exited.".format(",".join(map(str, child_pids)))
            )

        if returncode == 0:
            self.__logger.info(f"process has finished cleanly [pid {pid}]")
        else:
            self.__logger.error(
                "process has died [pid {}, exit code {}, cmd '{}'].".format(
                    pid, returncode, " ".join(filter(lambda part: part.strip(), cmd))
                )
            )
        await context.emit_event(ProcessExited(returncode=returncode, **process_event_args))
        # respawn the process if necessary
        if (
            not context.is_shutdown
            and self.__shutdown_future is not None
            and not self.__shutdown_future.done()
            and self.__respawn
            and (
                self.__respawn_max_retries < 0
                or self.__respawn_retries < self.__respawn_max_retries
            )
        ):
            # Increase the respawn_retries counter
            self.__respawn_retries += 1
            if self.__respawn_delay is not None and self.__respawn_delay > 0.0:
                # wait for a timeout(`self.__respawn_delay`) to respawn the process
                # and handle shutdown event with future(`self.__shutdown_future`)
                # to make sure `ros2 launch` exit in time
                await asyncio.wait((self.__shutdown_future,), timeout=self.__respawn_delay)
            if not self.__shutdown_future.done():
                context.asyncio_loop.create_task(self.__execute_process(context))
                return
        self.__cleanup()

    def prepare(self, context: LaunchContext):
        """Prepare the action for execution."""
        self.__process_description.prepare(context, self)

        # store packed kwargs for all ProcessEvent based events
        self.__process_event_args = {
            "action": self,
            "name": self.__process_description.final_name,
            "cmd": self.__process_description.final_cmd,
            "cwd": self.__process_description.final_cwd,
            "env": self.__process_description.final_env,
            # pid is added to the dictionary in the connection_made() method of the protocol.
        }

        self.__respawn = cast(bool, perform_typed_substitution(context, self.__respawn, bool))

    def execute(self, context: LaunchContext) -> Optional[List[LaunchDescriptionEntity]]:
        """
        Execute the action.

        This does the following:
        - register an event handler for the shutdown process event
        - register an event handler for the signal process event
        - register an event handler for the stdin event
        - configures logging for the IO process event
        - create a task for the coroutine that monitors the process
        """
        self.prepare(context)
        name = self.__process_description.final_name

        if self.__executed:
            raise RuntimeError(
                f"ExecuteLocalExt action '{name}': executed more than once: {self.describe()}"
            )
        self.__executed = True

        if context.is_shutdown:
            # If shutdown starts before execution can start, don't start execution.
            return None

        if self.__cached_output:
            on_output_method = self.__on_process_output_cached
            flush_buffers_method = self.__flush_cached_buffers
        else:
            on_output_method = self.__on_process_output
            flush_buffers_method = self.__flush_buffers

        event_handlers = [
            EventHandler(
                matcher=lambda event: is_a_subclass(event, ShutdownProcess),
                entities=OpaqueFunction(function=self.__on_shutdown_process_event),
            ),
            EventHandler(
                matcher=lambda event: is_a_subclass(event, SignalProcess),
                entities=OpaqueFunction(function=self.__on_signal_process_event),
            ),
            OnProcessIO(
                target_action=self,
                on_stdin=self.__on_process_stdin,
                on_stdout=lambda event: on_output_method(
                    event, self.__stdout_buffer, self.__stdout_logger
                ),
                on_stderr=lambda event: on_output_method(
                    event, self.__stderr_buffer, self.__stderr_logger
                ),
            ),
            OnShutdown(
                on_shutdown=self.__on_shutdown,
            ),
            OnProcessExit(
                target_action=self,
                # TODO: This is also a little strange, OnProcessExit shouldn't ever be able to
                # take a None for the callable, but this seems to be the default case?
                on_exit=self.__on_exit,  # type: ignore
            ),
            OnProcessExit(
                target_action=self,
                on_exit=flush_buffers_method,
            ),
        ]
        for event_handler in event_handlers:
            context.register_event_handler(event_handler)

        try:
            self.__completed_future = context.asyncio_loop.create_future()
            self.__shutdown_future = context.asyncio_loop.create_future()
            self.__logger = launch.logging.get_logger(name)
            if not isinstance(self.__output, dict):
                self.__stdout_logger, self.__stderr_logger = launch.logging.get_output_loggers(
                    name, perform_substitutions(context, self.__output)
                )
            else:
                self.__stdout_logger, self.__stderr_logger = launch.logging.get_output_loggers(
                    name, self.__output
                )
            context.asyncio_loop.create_task(self.__execute_process(context))
        except Exception:
            for event_handler in event_handlers:
                context.unregister_event_handler(event_handler)
            raise
        return None

    def get_asyncio_future(self) -> Optional[asyncio.Future]:
        """Return an asyncio Future, used to let the launch system know when we're done."""
        return self.__completed_future

    def get_stdout(self):
        """
        Get cached stdout.

        :raises RuntimeError: if cached_output is false.
        """
        if not self.__cached_output:
            raise RuntimeError(
                "cached output must be true to be able to get stdout,"
                f" proc '{self.__process_description.name}'"
            )
        return self.__stdout_buffer.getvalue()

    def get_stderr(self):
        """
        Get cached stdout.

        :raises RuntimeError: if cached_output is false.
        """
        if not self.__cached_output:
            raise RuntimeError(
                "cached output must be true to be able to get stderr, proc"
                f" '{self.__process_description.name}'"
            )
        return self.__stderr_buffer.getvalue()

    @property
    def return_code(self):
        """Get the process return code, None if it hasn't finished."""
        if self._subprocess_transport is None:
            return None
        return self._subprocess_transport.get_returncode()
