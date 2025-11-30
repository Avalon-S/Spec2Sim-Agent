import io
import contextlib
import traceback

def execute_code(code_str: str) -> dict:
    """
    Executes Python code safely using exec().
    Captures stdout, stderr.
    Returns { 'stdout': ..., 'stderr': ... }
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            exec(code_str, globals())
    except Exception:
        traceback.print_exc(file=stderr_capture)

    return {
        "stdout": stdout_capture.getvalue(),
        "stderr": stderr_capture.getvalue()
    }
