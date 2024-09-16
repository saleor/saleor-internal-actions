import sys
from pathlib import Path

import pytest

from grant_license_checker.cli_utils.files import cli_maybe_open_file


def test_cli_maybe_open_file_successfully(tmp_path: Path):
    """When opening an existing and valid file, it """
    (tmp_path := tmp_path / "dummy.json").touch(exist_ok=False)

    # Should not raise any errors while opening (nor exit).
    with cli_maybe_open_file(tmp_path, "r", default=sys.stdout) as fp:
        assert fp is not sys.stdout, "should not have used the default file"
        assert fp.name == str(tmp_path.absolute())
        assert fp.mode == "r"

    assert fp.closed is True, "should have closed the file"


@pytest.mark.parametrize("file_path", ["-", None])
def test_cli_opens_file_as_stdout(file_path):
    """When opening a file as stdout, it should not close the file."""

    with cli_maybe_open_file(file_path, "r", default=sys.stdout) as fp:
        assert fp is sys.stdout, "should have used the default file"

    assert fp.closed is False, "should not have closed the default file"


def test_cli_opens_non_existent_file(tmp_path: Path):
    """When opening a file as stdout, it should not close the file."""

    tmp_path = tmp_path / "dummy.json"

    with pytest.raises(SystemExit) as exc:
        with cli_maybe_open_file(tmp_path, "r", default=sys.stdout):
            pass

    assert isinstance(exc.value.__cause__, FileNotFoundError)
