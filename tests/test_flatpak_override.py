import configparser
import pytest

from dzgui.const.constants import FLATPAK_APPID, GTK_APP_ID, TMP_PATH
from dzgui.config.xdg import get_xdg_paths
from dzgui.util.flatpak import apply_overrides

PATHS_KEY = "Context"
PATHS_SUBKEY = "filesystems"
BUS_KEY = "Session Bus Policy"

pytestmark = pytest.mark.flatpak


@pytest.fixture
def xdg_paths() -> dict[str, str]:
    return get_xdg_paths()


@pytest.fixture
def override(xdg_paths) -> None:
    apply_overrides(xdg_paths)


@pytest.fixture
def config(xdg_paths) -> configparser.ConfigParser:
    conf_path = xdg_paths["XDG_DATA_HOME"].parent.joinpath(
        f"flatpak/overrides/{FLATPAK_APPID}"
    )
    config = configparser.ConfigParser()
    config.read(conf_path)
    return config


def test_session_bus(override, config) -> None:
    bus = config[BUS_KEY][GTK_APP_ID]
    assert bus == "own"


def test_paths(override, xdg_paths, config) -> None:
    expect: list[str] = []
    expect.append(TMP_PATH)
    expect.extend([*xdg_paths.values()])
    paths = config[PATHS_KEY][PATHS_SUBKEY].split(";")
    assert all(str(path) in paths for path in expect)
