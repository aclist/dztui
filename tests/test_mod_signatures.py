import pytest
import shutil
import tempfile

from pathlib import Path
from typing import TYPE_CHECKING

import dzgui.api.mods
import dzgui.config.query

from tests.fixtures import fixture_path

if TYPE_CHECKING:
    from dzgui.const.enums import Preferences

pytestmark = pytest.mark.mods

@pytest.fixture
def versions() -> str:
    return fixture_path("dzg.versions")

@pytest.fixture
def tmp() -> str:
    with tempfile.NamedTemporaryFile(delete=False) as f:
        tmp = f.name
    return tmp

def mock_local_ids(path: Path) -> list[int]:
    return [3410710885, 3739934289]

def mock_lookup(path: Path, prefs: "Preferences") -> str:
    return ""

def test_signatures(monkeypatch, tmp: str, versions: str) -> None:
    ids = [1559212036, 1654462998]
    shutil.copyfile(versions, tmp)
    path = Path(tmp)
    monkeypatch.setattr("dzgui.api.mods.lookup", mock_lookup)
    dzgui.api.mods.remove_stale_signatures(path, path, ids)
    with open(tmp, "r") as f:
        lines = f.readlines()
    assert ids not in lines

def test_signatures_with_no_ids(monkeypatch, tmp: str, versions: str) -> None:
    shutil.copyfile(versions, tmp)
    path = Path(tmp)
    monkeypatch.setattr("dzgui.api.mods.get_local_mod_ids", mock_local_ids)
    monkeypatch.setattr("dzgui.api.mods.lookup", mock_lookup)
    dzgui.api.mods.remove_stale_signatures(path, path)
    with open(tmp, "r") as f:
        lines = f.readlines()
    assert lines == ["3410710885,1752864732\n", "3739934289,1780855136\n"]
