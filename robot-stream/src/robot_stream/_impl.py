from pathlib import Path
from typing import Dict, Iterator, Optional, Callable
import json
import itertools
import string
import datetime


_valid_chars = tuple(string.ascii_letters + string.digits)


def _gen_id(level: int = 1) -> Iterator[str]:
    iter_in = tuple(_valid_chars for _ in range(level))
    for entry in itertools.product(*iter_in):
        yield "".join(entry)

    # Recursively generate ids...
    yield from _gen_id(level + 1)


class _RobotOutputImpl:
    def __init__(
        self,
        output_dir: Optional[str],
        port: int,
        write: Optional[Callable[[str], None]] = None,
        initial_time: Optional[datetime.datetime] = None,
        robot_version: Optional[str] = None,
    ):
        self._written_initial = False

        # Base memory for all streams (rotated or not)
        self._base_memo: Dict[str, str] = {}

        # Memory just for the current stream (if a name is not
        # here it has to be added because the output was rotated).
        self._current_memo: Dict[str, str] = {}

        if output_dir is None:
            self._output_dir = None
        else:
            self._output_dir = Path(output_dir)
            self._output_dir.mkdir(exist_ok=True)
        self._write = write

        self._port = port

        self._move_old_runs()

        self._current_entry = -1
        self._current_file: Path
        self._stream = None

        if initial_time is None:
            initial_time = datetime.datetime.now()
        self._initial_time = initial_time

        self._robot_version = robot_version

        self._rotate_output()
        self._id_generator = _gen_id()

    @property
    def current_file(self):
        return self._current_file

    @property
    def initial_time(self) -> datetime.datetime:
        return self._initial_time

    def _rotate_output(self):
        import sys

        if self._output_dir is not None:
            self._current_memo = {}

            self._current_entry += 1
            self._current_file = (
                self._output_dir / f"robot_stream.{self._current_entry}.rfstream"
            )
            if self._stream is not None:
                self._stream.close()
                self._stream = None

            self._stream = self._current_file.open("w", encoding="utf-8")
            self._written_initial = False

        if not self._written_initial:
            print("Writing logs to", self._current_file.absolute())
            self._write_json("V ", 1)
            self._write_json("I ", f"sys.platform={sys.platform}")
            self._write_json("I ", f"python={sys.version}")

            robot_version = self._robot_version
            if robot_version is None:
                import robot

                robot_version = robot.get_version()

            self._write_json("I ", f"robot={robot_version}")
            self._write_with_separator(
                "T ", (self._initial_time.isoformat(timespec="milliseconds"),)
            )
            self._written_initial = True

    def _write_json(self, msg_type, args):
        args_as_str = json.dumps(args)
        s = f"{msg_type}{args_as_str}\n"
        if self._write is not None:
            self._write(s)
        self._stream.write(s)
        self._stream.flush()

    def _write_with_separator(self, msg_type, args):
        args_as_str = "|".join(args)
        s = f"{msg_type}{args_as_str}\n"
        if self._write is not None:
            self._write(s)
        self._stream.write(s)
        self._stream.flush()

    def get_time_delta(self) -> float:
        delta = datetime.datetime.now() - self._initial_time
        return round(delta.total_seconds(), 3)

    def _move_old_runs(self):
        pass
        # TODO: Handle old runs (move to old runs).
        # for entry in self._output_dir.iterdir():
        #     print(entry)

    def _gen_id(self) -> str:
        while True:
            gen = next(self._id_generator)
            if gen not in self._base_memo:
                return gen

    def _obtain_id(self, s: str) -> str:
        curr_id = self._current_memo.get(s)
        if curr_id is not None:
            return curr_id

        curr_id = self._base_memo.get(s)
        if curr_id is not None:
            self._write_json(f"M {curr_id}:", s)
            self._current_memo[s] = curr_id

        new_id = self._gen_id()
        self._write_json(f"M {new_id}:", s)
        self._base_memo[s] = new_id
        self._current_memo[s] = new_id
        return new_id

    def _number(self, v):
        return str(v)

    def start_suite(self, name, suite_id, suite_source, time_delta):
        oid = self._obtain_id
        self._write_with_separator(
            "SS ",
            [
                oid(name),
                oid(suite_id),
                oid(suite_source),
                self._number(time_delta),
            ],
        )

    def end_suite(self, status, time_delta):
        oid = self._obtain_id
        self._write_with_separator(
            "ES ",
            [
                oid(status),
                self._number(time_delta),
            ],
        )

    def start_test(self, name, test_id, test_line, time_delta):
        oid = self._obtain_id
        self._write_with_separator(
            "ST ",
            [
                oid(name),
                oid(test_id),
                self._number(test_line),
                self._number(time_delta),
            ],
        )

    def end_test(self, status, message, time_delta):
        oid = self._obtain_id
        self._write_with_separator(
            "ET ",
            [
                oid(status),
                oid(message),
                self._number(time_delta),
            ],
        )

    def start_keyword(
        self, name, libname, keyword_type, doc, source, lineno, start_time_delta, args
    ):
        oid = self._obtain_id
        self._write_with_separator(
            "SK ",
            [
                oid(name),
                oid(libname),
                oid(keyword_type),
                oid(doc),
                oid(source),
                self._number(lineno),
                self._number(start_time_delta),
            ],
        )

        if args:
            for arg in args:
                self._write_with_separator(
                    "KA ",
                    [
                        oid(arg),
                    ],
                )

    def end_keyword(self, status, time_delta):
        oid = self._obtain_id
        self._write_with_separator(
            "EK ",
            [
                oid(status),
                self._number(time_delta),
            ],
        )
