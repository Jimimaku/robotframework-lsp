import json
import datetime


class RFStream:

    # V3 would be nicer but it doesn't support keywords...
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, *args, **kwargs):
        from robot_stream._impl import _RobotOutputImpl
        import sys

        for arg in args:
            if arg.startswith("--dir="):
                kwargs["--dir"] = arg[6:]
            if arg.startswith("--port="):
                kwargs["--port"] = arg[7:]

        output_dir = kwargs.get("--dir", ".").replace("<COLON>", ":")
        port = int(kwargs.get("--port", "-1"))

        # Attributes expected to be used just when used in-memory.
        write = kwargs.get("__write__")
        initial_time = kwargs.get("__initial_time__")
        robot_version = kwargs.get("__robot_version__")

        self._robot_output_impl = _RobotOutputImpl(
            output_dir,
            port,
            write=write,
            initial_time=initial_time,
            robot_version=robot_version,
        )

    @property
    def robot_output_impl(self):
        return self._robot_output_impl

    @property
    def initial_time(self) -> datetime.datetime:
        return self._robot_output_impl.initial_time

    def _get_time_delta(self, attributes) -> float:
        # i.e.: in general the time delta will not be there
        # it's only there for the case when we're reading
        # from the output.xml.
        time_delta = attributes.get("timedelta")
        if time_delta is not None:
            return time_delta
        return self._robot_output_impl.get_time_delta()

    def start_suite(self, name, attributes):
        # {
        #     "id": "s1",
        #     "longname": "Robot1",
        #     "doc": "",
        #     "metadata": {},
        #     "starttime": "20221003 14:20:02.195",
        #     "tests": ["First task", "Second task"],
        #     "suites": [],
        #     "totaltests": 2,
        #     "source": "C:\\Users\\...\\robot1.robot",
        # }
        return self._robot_output_impl.start_suite(
            name,
            attributes["id"],
            attributes["source"],
            self._get_time_delta(attributes),
        )

    def end_suite(self, name, attributes):
        # {
        #     "id": "s1",
        #     "longname": "Robot1",
        #     "doc": "",
        #     "metadata": {},
        #     "starttime": "20221004 09:38:40.271",
        #     "endtime": "20221004 09:38:40.323",
        #     "elapsedtime": 52,
        #     "status": "FAIL",
        #     "message": "",
        #     "tests": ["First task", "Second task"],
        #     "suites": [],
        #     "totaltests": 2,
        #     "source": "C:\\Users\\fabio\\AppData\\Local\\Temp\\pytest-of-fabio\\pytest-184\\test_robot_stream0\\test_robot_stream\\robot1.robot",
        #     "statistics": "2 tasks, 1 passed, 1 failed",
        # }
        return self._robot_output_impl.end_suite(
            attributes["status"], self._get_time_delta(attributes)
        )

    def start_test(self, name, attributes):
        # {
        #     "id": "s1-t1",
        #     "longname": "Robot1.First task",
        #     "doc": "",
        #     "tags": [],
        #     "lineno": 11,
        #     "source": "C:\\Users\\fabio\\...\\robot1.robot",
        #     "starttime": "20221003 14:20:02.231",
        #     "template": "",
        #     "originalname": "First task",
        # }
        return self._robot_output_impl.start_test(
            name,
            attributes["id"],
            attributes.get(
                "lineno"
            ),  # The source is already given by the suite (no need to repeat)
            self._get_time_delta(attributes),
        )

    def end_test(self, name, attributes):
        # {
        #     "id": "s1-t2",
        #     "longname": "Robot1.Second task",
        #     "doc": "",
        #     "tags": [],
        #     "lineno": 15,
        #     "source": "C:\\Users\\fabio\\AppData\\Local\\Temp\\pytest-of-fabio\\pytest-187\\test_robot_stream0\\test_robot_stream\\robot1.robot",
        #     "starttime": "20221004 16:23:10.403",
        #     "endtime": "20221004 16:23:10.412",
        #     "elapsedtime": 9,
        #     "status": "FAIL",
        #     "message": "Failed execution for some reason...",
        #     "template": "",
        #     "originalname": "Second task",
        # }
        return self._robot_output_impl.end_test(
            attributes["status"],
            attributes["message"],
            self._get_time_delta(attributes),
        )

    def start_keyword(self, name, attributes):
        # {
        #     "doc": "Does absolutely nothing.",
        #     "assign": [],
        #     "tags": [],
        #     "lineno": 7,
        #     "source": "C:\\Users\\fabio\\AppData\\Local\\Temp\\pytest-of-fabio\\pytest-170\\test_robot_stream0\\test_robot_stream\\robot1.robot",
        #     "type": "KEYWORD",
        #     "status": "NOT SET",
        #     "starttime": "20221003 16:20:21.234",
        #     "kwname": "No Operation",
        #     "libname": "BuiltIn",
        #     "args": [],
        # }
        return self._robot_output_impl.start_keyword(
            attributes["kwname"],
            attributes.get("libname"),
            attributes.get("type"),
            attributes.get("doc"),
            attributes.get("source"),
            attributes.get("lineno"),
            self._get_time_delta(attributes),
            attributes.get("args"),
        )

    def end_keyword(self, name, attributes):
        # {
        #     "doc": "Does absolutely nothing.",
        #     "assign": [],
        #     "tags": [],
        #     "lineno": 7,
        #     "source": "C:\\Users\\fabio\\AppData\\Local\\Temp\\pytest-of-fabio\\pytest-191\\test_robot_stream0\\test_robot_stream\\robot1.robot",
        #     "type": "KEYWORD",
        #     "status": "PASS",
        #     "starttime": "20221004 16:27:46.959",
        #     "endtime": "20221004 16:27:46.959",
        #     "elapsedtime": 0,
        #     "kwname": "No Operation",
        #     "libname": "BuiltIn",
        #     "args": [],
        # }
        return self._robot_output_impl.end_keyword(
            attributes["status"], self._get_time_delta(attributes)
        )

    def log_message(self, message):
        # {
        #     "timestamp": "20221019 10:00:07.928",
        #     "message": "{'timestamp': '20221019 10:00:07.928', 'message': '1', 'level': 'INFO', 'html': 'no'}",
        #     "level": "INFO",
        #     "html": "no",
        # }
        pass


def iter_decoded_log_format(stream):
    from ._decoder import iter_decoded_log_format

    return iter_decoded_log_format(stream)
