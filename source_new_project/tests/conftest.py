from pathlib import Path

import pytest


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    return tmp_path
