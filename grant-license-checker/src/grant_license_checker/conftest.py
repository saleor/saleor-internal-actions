from pathlib import Path

import pytest
from .models.grant_json import GrantResponse


def get_fixture(filename: str) -> Path:
    """Return the selected fixture from ./tests/fixtures/."""
    root_dir = (Path(__file__).parent / "tests" / "fixtures").resolve().absolute()
    path = (
        root_dir.joinpath(filename)
        .resolve()
    )
    if path.is_relative_to(root_dir) is False:
        raise ValueError(f"{path} is not in the subpath of {root_dir}")
    if path.exists() is False:
        raise FileNotFoundError(str(path))
    return path


@pytest.fixture
def grant_json_report() -> GrantResponse:
    return GrantResponse.model_validate_json(
        get_fixture("sample-grant-report.json").read_text()
    )
