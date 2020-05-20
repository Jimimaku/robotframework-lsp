from contextlib import contextmanager
import os
import sys
import threading
from robocode_ls_core.options import USE_TIMEOUTS, NO_TIMEOUT
import pytest


TIMEOUT = int(os.getenv("PYTEST_TIMEOUT", 7))
if not USE_TIMEOUTS:
    TIMEOUT = NO_TIMEOUT  # i.e.: None


def wait_for_test_condition(condition, msg=None, timeout=TIMEOUT, sleep=1 / 20.0):
    from robocode_ls_core.basic import wait_for_condition as w

    return w(condition, msg=msg, timeout=timeout, sleep=sleep)


@pytest.fixture
def ws_root_path(tmpdir):
    return str(tmpdir.join("root"))


@pytest.fixture(autouse=True)
def config_logger(tmpdir):
    from robocode_ls_core.robotframework_log import configure_logger

    configure_logger("test", 2, None)


@contextmanager
def communicate_lang_server(
    write_to, read_from, language_server_client_class=None, kwargs={}
):
    if language_server_client_class is None:
        from robocode_ls_core.unittest_tools.language_server_client import (
            _LanguageServerClient,
        )

        language_server_client_class = _LanguageServerClient

    from robocode_ls_core.jsonrpc.streams import JsonRpcStreamWriter
    from robocode_ls_core.jsonrpc.streams import JsonRpcStreamReader

    w = JsonRpcStreamWriter(write_to, sort_keys=True)
    r = JsonRpcStreamReader(read_from)

    language_server = language_server_client_class(w, r, **kwargs)
    try:
        yield language_server
    finally:
        if language_server.require_exit_messages:
            language_server.shutdown()
            language_server.exit()


@contextmanager
def start_language_server_tcp(log_file, main_method, language_server_class):
    """
    Starts a language server in the same process and communicates through tcp.
    
    Yields a language server client.
    """
    import socket
    from robocode_ls_core.unittest_tools.monitor import dump_threads

    class _LanguageServerConfig(object):

        address = None

    config = _LanguageServerConfig()
    start_event = threading.Event()
    finish_event = threading.Event()
    language_server_instance_final = []

    def after_bind(server):
        address = server.socket.getsockname()
        config.address = address
        start_event.set()

    def start_language_server():
        def new_language_server_class(*args, **kwargs):
            language_server_instance = language_server_class(*args, **kwargs)
            language_server_instance_final.append(language_server_instance)
            return language_server_instance

        main_method(
            [
                "--tcp",
                "--host=127.0.0.1",
                "--port=0",
                "-vv",
                "--log-file=%s" % log_file,
            ],
            after_bind=after_bind,
            language_server_class=new_language_server_class,
        )
        finish_event.set()

    t = threading.Thread(target=start_language_server, name="Language Server", args=())
    t.start()

    assert start_event.wait(TIMEOUT)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(config.address)
    write_to = s.makefile("wb")
    read_from = s.makefile("rb")
    with communicate_lang_server(write_to, read_from) as lang_server_client:
        wait_for_test_condition(lambda: len(language_server_instance_final) == 1)
        lang_server_client.language_server_instance = language_server_instance_final[0]
        yield lang_server_client

    if not finish_event.wait(TIMEOUT):
        dump_threads()
        raise AssertionError(
            "Language server thread did not exit in the available timeout."
        )


@contextmanager
def create_language_server_process(log_file, __main__module):
    from robocode_ls_core.basic import kill_process_and_subprocesses

    import subprocess

    language_server_process = subprocess.Popen(
        [
            sys.executable,
            "-u",
            __main__module.__file__,
            "-vv",
            "--log-file=%s" % log_file,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )
    returncode = language_server_process.poll()
    assert returncode is None
    try:
        yield language_server_process
    finally:
        returncode = language_server_process.poll()
        if returncode is None:
            kill_process_and_subprocesses(language_server_process.pid)


@pytest.fixture
def log_file(tmpdir):
    logs_dir = tmpdir.join("logs")
    logs_dir.mkdir()
    filename = str(logs_dir.join("log_test.log"))
    sys.stderr.write("Logging subprocess to: %s" % (filename,))

    yield filename

    for name in os.listdir(str(logs_dir)):
        print("\n--- %s contents:" % (name,))
        with open(str(logs_dir.join(name)), "r") as stream:
            print(stream.read())


@pytest.fixture
def language_server_tcp(log_file, main_module, language_server_class):
    """
    Starts a language server in the same process and communicates through tcp.
    """

    with start_language_server_tcp(
        log_file, main_module.main, language_server_class
    ) as lang_server_client:
        yield lang_server_client


@pytest.fixture
def language_server_process(log_file, main_module):
    with create_language_server_process(log_file, main_module) as process:
        yield process


@pytest.fixture
def language_server_io(language_server_process):
    """
    Starts a language server in a new process and communicates through stdin/stdout streams.
    """
    write_to = language_server_process.stdin
    read_from = language_server_process.stdout

    with communicate_lang_server(write_to, read_from) as lang_server_client:
        yield lang_server_client


@pytest.fixture(params=["io", "tcp"])
def language_server(request):
    if request.param == "io":
        return request.getfixturevalue("language_server_io")
    else:
        return request.getfixturevalue("language_server_tcp")
