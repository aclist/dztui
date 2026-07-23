import pytest
import tempfile

from pathlib import Path
from _pytest.monkeypatch import MonkeyPatch

from dzgui.api.shortcuts import Shortcuts
from tests.fixtures import fixture_path

pytestmark = pytest.mark.apitest


def mock_find_shortcuts(self, steam_path: Path) -> Path:
    return Path(fixture_path("api/no_shortcuts.vdf"))


@pytest.fixture(scope="module", autouse=True)
def patch_api() -> None:
    mp = MonkeyPatch()
    mp.setattr("dzgui.api.shortcuts.Shortcuts.find_shortcuts_path", mock_find_shortcuts)
    yield
    mp.undo()


def test_no_shortcuts(monkeypatch) -> None:
    s = Shortcuts(Path(""))
    assert len(s.shortcuts["shortcuts"]) == 0


@pytest.fixture
def dummy_app() -> None:
    d = {
        "AppName": "TEST APP",
        "StartDir": "TEST_DIR",
        "Exe": "TEST_DIR/TEST_EXE.EXE",
        "icon": "IMAGES_DIR/TEST_IMAGE.PNG",
    }
    return d


def test_wrap_exe(dummy_app: dict[str, str]) -> None:
    s = Shortcuts(Path(""))
    s.add_shortcut(*dummy_app.values())
    assert s.shortcuts["shortcuts"]["0"]["Exe"][0] == '"'
    assert s.shortcuts["shortcuts"]["0"]["Exe"][-1] == '"'


def test_add_shortcut(dummy_app: dict[str, str]) -> None:
    s = Shortcuts(Path(""))
    s.add_shortcut(*dummy_app.values())
    new = s.shortcuts["shortcuts"]
    ind = str(len(new) - 1)
    for k, v in dummy_app.items():
        if k == "Exe":
            v = f'"{v}"'
        assert new[ind][k] == v


def test_save_shortcut(dummy_app: dict[str, str]) -> None:
    s = Shortcuts(Path(""))
    s.add_shortcut(*dummy_app.values())
    with tempfile.NamedTemporaryFile() as f:
        tmp = Path(f.name)
        s.shortcuts_path = tmp
        s.save_shortcuts()
        s._load_shortcuts(tmp)
        assert len(s.shortcuts["shortcuts"]) == 1


def test_shortcut_crc(dummy_app: dict[str, str]) -> None:
    s = Shortcuts(Path(""))
    s.add_shortcut(*dummy_app.values())
    for key in s.shortcuts["shortcuts"].keys():
        entry = s.shortcuts["shortcuts"][key]
        name = entry["AppName"]
        exe = entry["Exe"]
        uid = name + exe
        bpid = s.gen_bpid(uid)
        assert entry["appid"] & 0xFFFFFFFF == bpid


def test_reverse_crc(dummy_app: dict[str, str]) -> None:
    s = Shortcuts(Path(""))
    s.add_shortcut(*dummy_app.values())
    for key in s.shortcuts["shortcuts"].keys():
        entry = s.shortcuts["shortcuts"][key]
        name = entry["AppName"]
        exe = entry["Exe"]
        uid = name + exe
        bpid = s.gen_bpid(uid)
        assert s.find_appname_by_unsigned_id(bpid) == name
