from contextlib import contextmanager
import functools


@contextmanager
def after(obj, method_name, callback):
    original_method = getattr(obj, method_name)

    @functools.wraps(original_method)
    def new_method(*args, **kwargs):
        ret = original_method(*args, **kwargs)
        callback(*args, **kwargs)
        return ret

    setattr(obj, method_name, new_method)
    try:
        yield
    finally:
        setattr(obj, method_name, original_method)


def test_robot_stream(datadir):
    import robot
    from robot_stream import RFStream, iter_decoded_log_format
    from io import StringIO
    from pathlib import Path

    created = []

    def on_created(robot_stream, *args, **kwargs):
        print("Created", robot_stream)
        created.append(robot_stream)

    show_contents = False
    show_out_as_json_str = True
    build_contents_locally = True

    outdir = datadir / "out"
    if build_contents_locally:
        outdir = Path(
            r"D:\x\vscode-robot\robotframework-lsp\robot-stream\tests\robot_stream_tests\test_robot_stream"
        )

    with after(RFStream, "__init__", on_created):
        outdir_to_listener = str(outdir).replace(":", "<COLON>")
        robot1 = datadir / "robot1.robot"
        xml_output = outdir / "output.xml"
        report_output = outdir / "report.html"
        log_output = outdir / "log.html"
        robot.run_cli(
            [
                "-l",
                str(log_output),
                "-r",
                str(report_output),
                "-o",
                str(xml_output),
                "--listener",
                f"robot_stream.RFStream:--dir={outdir_to_listener}",
                str(robot1),
            ],
            exit=False,
        )

    assert len(created) == 1
    robot_stream = created[0]
    impl = robot_stream.robot_output_impl
    assert impl.current_file.exists()
    print("Contents of: ", impl.current_file)
    print("-----")
    contents = impl.current_file.read_text("utf-8")
    if show_contents:
        print(contents)

    if show_out_as_json_str:
        import json

        print(repr(json.dumps(contents)))
    print("-----")
    print(f"Size: {len(contents)/8} bytes")
    print("-----")

    decoded_len = 0
    for line in iter_decoded_log_format(StringIO(contents)):
        if show_contents:
            print(line)
        decoded_len += len(line)
    print(f"Decoded size: {decoded_len/8} bytes")
    print(f"output.xml size: {xml_output.stat().st_size/8} bytes")

    from robot_stream.xml_to_rfstream import (
        convert_xml_to_rfstream,
    )

    txt = xml_output.read_text("utf-8")

    import io

    source = io.StringIO()
    source.write(txt)
    source.seek(0)

    def write(s):
        if show_contents:
            sys.stdout.write(s)

    convert_xml_to_rfstream(source, write=write)


def test_gen_id(data_regression):
    from robot_stream._impl import _gen_id

    iter_in = _gen_id()
    generated = []
    for _ in range(200):
        generated.append(next(iter_in))

    data_regression.check(generated)
