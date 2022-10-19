import xml.sax
import sys
import datetime
from typing import Optional, Callable


class _RobotData:
    def __init__(self, attrs):
        self.attrs = attrs
        self.status = None


class _SuiteData:
    def __init__(self, attrs):
        self.attrs = attrs
        self.status = None


class _TestData:
    def __init__(self, attrs):
        self.attrs = attrs
        self.status = None


class _KeywordData:
    def __init__(self, attrs):
        self.attrs = attrs
        self.status = None

        self.args = []
        self.doc = ""
        self.sent = False


class _Status:
    def __init__(self, attrs):
        self.attrs = attrs

    @property
    def status(self):
        return self.attrs["status"]

    @property
    def endtime(self):
        return self.attrs["endtime"]

    @property
    def starttime(self):
        return self.attrs["starttime"]

    def compute_timedelta(self, initial_time):
        endtime = parse_time(self.endtime)
        delta = endtime - initial_time
        return round(delta.total_seconds(), 3)


class _XmlSaxParser(xml.sax.ContentHandler):
    """
    Notes:

    - Log messages are unscoped (they just appear as errors in the
      end and thus we can't know what was the current keyword).

    - The start/end time is written as the last thing in the
      element along with the status, so, we don't write the
      start time, we just write the end time (we could write
      the start time, but then we'd need to keep all the children
      in memory, at which point we could just be working with
      ElementTree instead of sax parsing as we'd need to have
      almost everything in memory for it to work).
    """

    def __init__(self, create_listener):
        self._create_listener = create_listener
        self._listener = None
        self._stack = []
        self._need_chars = False
        self._chars = []

    def startElement(self, name, attrs):
        method = getattr(self, "start_" + name, None)
        if method:
            method(attrs)
        # else:
        #     print("Unhandled start:", name)

    def endElement(self, name):
        method = getattr(self, "end_" + name, None)
        if method:
            method()
        # else:
        #     print("Unhandled end:", name)

    def start_robot(self, attrs):
        assert self._listener is None
        self._listener = self._create_listener(attrs)
        self._stack.append(_RobotData(attrs))

    def end_robot(self):
        del self._stack[-1]

    def start_suite(self, attrs):
        self.send_delayed()
        name = attrs.get("name")
        suiteid = attrs.get("id")
        source = attrs.get("source")
        if name and suiteid:
            self._stack.append(_SuiteData(attrs))
            self._listener.start_suite(
                name, {"id": suiteid, "source": source, "timedelta": -1}
            )
        else:
            self._stack.append(None)

    def end_suite(self):
        self.send_delayed()
        s = self._stack.pop(-1)
        if s is not None:
            status = s.status.attrs["status"]
            self._listener.end_suite(
                s.attrs["name"], {"status": status, "timedelta": -1}
            )

    def start_test(self, attrs):
        self.send_delayed()
        name = attrs.get("name")
        suiteid = attrs.get("id")
        line = attrs.get("line")
        if name and suiteid:
            self._stack.append(_TestData(attrs))
            self._listener.start_test(
                name, {"id": suiteid, "lineno": line, "timedelta": -1}
            )
        else:
            self._stack.append(None)

    def end_test(self):
        self.send_delayed()
        s = self._stack.pop(-1)
        if s is not None:
            status = s.status.status

            self._listener.end_test(
                s.attrs["name"],
                {
                    "status": status,
                    "timedelta": s.status.compute_timedelta(
                        self._listener.initial_time
                    ),
                    "message": "",
                },
            )

    def start_kw(self, attrs):
        name = attrs.get("name")
        if name:
            self.send_delayed()
            self._stack.append(_KeywordData(attrs))

            # We can't send it right away because we need the args which will
            # just appear afterwards...
        else:
            self._stack.append(None)

    def send_delayed(self):
        self.send_kw()

    def send_kw(self):
        if not self._stack:
            return

        peek = self._stack[-1]
        if isinstance(peek, _KeywordData):
            if not peek.sent:
                attrs = peek.attrs
                name = attrs.get("name")
                libname = attrs.get("libname")
                doc = peek.doc
                args = peek.args
                self._listener.start_keyword(
                    name,
                    {
                        "kwname": name,
                        "libname": libname,
                        "doc": doc,
                        "args": args,
                        "type": "KEYWORD",
                        "timedelta": -1,
                    },
                )

    def end_kw(self):
        self.send_delayed()
        s = self._stack.pop(-1)
        if s is not None:
            status = s.status.status

            self._listener.end_keyword(
                s.attrs["name"],
                {
                    "status": status,
                    "timedelta": s.status.compute_timedelta(
                        self._listener.initial_time
                    ),
                    "message": "",
                },
            )

    def start_arg(self, attrs):
        self._need_chars = True

    def end_arg(self):
        self._need_chars = False
        content = "".join(self._chars)
        self._chars = []
        if self._stack:
            peek = self._stack[-1]
            if isinstance(peek, _KeywordData):
                peek.args.append(content)

    def start_doc(self, attrs):
        self._need_chars = True

    def end_doc(self):
        self._need_chars = False
        content = "".join(self._chars)
        self._chars = []
        if self._stack:
            peek = self._stack[-1]
            if isinstance(peek, _KeywordData):
                peek.doc = content

    def characters(self, content):
        if self._need_chars:
            self._chars.append(content)

    def start_status(self, attrs):
        self.send_delayed()
        if self._stack:
            self._stack[-1].status = _Status(attrs)

    def end_status(self):
        pass  # no-op


def parse_time(date_str):
    return datetime.datetime.strptime(date_str, "%Y%m%d %H:%M:%S.%f")


def convert_xml_to_rfstream(source, write: Optional[Callable[[str], None]] = None):
    """
    :param source:
        Either a string pointing to the path to be parsed or some stream-like
        object with the contents.

    :param write:
        A callable to be used to write the contents received (sent line-by-line).
    """
    from robot_stream import RFStream

    if write is None:

        def write(s):
            sys.stdout.write(s)

    def create_listener(robot_attrs):
        initial_date_str = robot_attrs["generated"]
        initial_time = parse_time(initial_date_str)
        listener = RFStream(
            __write__=write,
            __initial_time__=initial_time,
            __robot_version__="<not loaded>",
        )
        return listener

    xml.sax.parse(source, _XmlSaxParser(create_listener))
