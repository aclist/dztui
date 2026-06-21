import pytest
from pathlib import Path

from dzgui.api.mods import tokenize
from tests.fixtures import fixture_path

@pytest.mark.mods
@pytest.mark.parametrize("i", range(1, 7))
def test_modmeta(i: int) -> None:
    fixture = fixture_path(f"cpp/mod{i}")
    path = Path(fixture)
    meta = tokenize(path)
    assert meta["name"] == "ModName"
