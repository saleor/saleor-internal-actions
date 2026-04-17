import contextlib
import logging
from pathlib import Path
from typing import TextIO, ContextManager

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def cli_maybe_open_file(
    path: Path | str | None, mode: str, default: TextIO
) -> ContextManager[TextIO]:
    """
    Attempts to open a given file, if it doesn't then it exits with an error immediately.

    If the path is null or '-', then it uses `default`.

    File closing behavior:
        - When `default` is used, the file will NOT be closed.
        - Otherwise, the file is closed.
    """
    if default and path in ("-", None):
        yield default
        # Do not close the file, the caller is responsible for it.
        return

    try:
        out_fp = open(path, mode)
    except OSError as exc:
        logger.error("Failed to open the file at %s: %s", path, exc)
        # Reraise the exception in order to be able to assert the parent
        # exception in tests.
        raise SystemExit(1) from exc

    yield out_fp
    out_fp.close()
