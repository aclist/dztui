import pytest
from dzgui.api.mods import tokenize
from tests.fixtures import fixture_path

@pytest.mark.mods
@pytest.mark.parametrize("fixture", [
    fixture_path("cpp/meta1.cpp"),
    fixture_path("cpp/meta2.cpp"),
    fixture_path("cpp/meta3.cpp"),
    fixture_path("cpp/meta4.cpp"),
    fixture_path("cpp/meta5.cpp"),
    fixture_path("cpp/meta6.cpp"),
    ]
)
def test_modmeta(fixture: str) -> None:
    meta = tokenize(fixture)
    assert meta["name"] == "ModName"
