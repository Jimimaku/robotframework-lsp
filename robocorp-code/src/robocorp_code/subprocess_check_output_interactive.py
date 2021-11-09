from robocorp_ls_core.robotframework_log import get_logger
import threading
from typing import Optional, List

log = get_logger(__name__)


def check_output_interactive(*popenargs, timeout=None, **kwargs) -> bytes:
    """
    This has the same API as subprocess.check_output, but allows us to work with
    the contents being generated by the subprocess before the subprocess actually
    finishes.

    :param on_stderr:
        A callable(string) (called from another thread) whenever output is
        written with stderr contents.

    :param on_stdout:
        A callable(string) (called from another thread) whenever output is
        written with stdout contents.

    :return: the stdout generated by the command.
    """
    from robocorp_ls_core.subprocess_wrapper import subprocess
    from robocorp_ls_core.basic import kill_process_and_subprocesses

    if kwargs.get("stdout", subprocess.PIPE) != subprocess.PIPE:
        raise AssertionError("stdout must be subprocess.PIPE")

    if kwargs.get("stderr", subprocess.PIPE) != subprocess.PIPE:
        # We could potentially also accept `subprocess.STDOUT`, but let's leave
        # this as a future improvement for now.
        raise AssertionError("stderr must be subprocess.PIPE")

    kwargs["stdout"] = subprocess.PIPE
    kwargs["stderr"] = subprocess.PIPE

    on_stderr = kwargs.pop("on_stderr")
    on_stdout = kwargs.pop("on_stdout")
    stdout_contents: List[bytes] = []
    stderr_contents: List[bytes] = []

    def stream_reader(stream, callback, contents_list: List[bytes]):
        for line in iter(stream.readline, b""):
            contents_list.append(line)
            callback(line)

    with subprocess.Popen(*popenargs, **kwargs) as process:
        threads = [
            threading.Thread(
                target=stream_reader, args=(process.stdout, on_stdout, stdout_contents)
            ),
            threading.Thread(
                target=stream_reader, args=(process.stderr, on_stderr, stderr_contents)
            ),
        ]
        for t in threads:
            t.start()

        retcode: Optional[int]
        try:
            try:
                retcode = process.wait(timeout)
            except:
                # i.e.: KeyboardInterrupt / TimeoutExpired
                retcode = process.poll()

                if retcode is None:
                    # It still hasn't completed: kill it.
                    try:
                        kill_process_and_subprocesses(process.pid)
                    except:
                        log.exception("Error killing pid: %s" % (process.pid,))

                    retcode = process.wait()
                raise

        finally:
            for t in threads:
                t.join()

        if retcode:
            raise subprocess.CalledProcessError(
                retcode,
                process.args,
                output=b"".join(stdout_contents),
                stderr=b"".join(stderr_contents),
            )

        return b"".join(stdout_contents)