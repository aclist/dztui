import pytest
from pathlib import Path


import dzgui.api.pefile as PeFile
from dzgui.api.steam import (
    VDFLoadError,
    AppNotInstalledError,
    AppMovedError,
    get_app_path
)

from dzgui.config.query import get_config
from dzgui.config.xdg import get_xdg_paths, parse_filepaths
from dzgui.const.constants import APPID_DAYZ

from tests.fixtures import fixture_path

pytestmark = pytest.mark.apitest


@pytest.fixture
def default_steam_path():
    paths = get_xdg_paths()
    xdg = parse_filepaths(paths)
    conf = get_config(xdg.config)
    return conf["default_steam_path"]


# TODO: split into separate test file
# FIXME: use fixtures
def test_pefile_length(default_steam_path):
    try:
        pe_file_path = PeFile.get_pefile_path(Path(default_steam_path), APPID_DAYZ)
        vers = PeFile.get_dayz_version(pe_file_path)
        st = PeFile.dayz_version_to_str(vers).split(".")
    except Exception as e:
        raise e
    assert len(st) == 3


def test_invalid_pefile_path():
    with pytest.raises(VDFLoadError):
        try:
            PeFile.get_pefile_path(Path("/not/a/path"), APPID_DAYZ)
        except Exception as e:
            raise e


@pytest.mark.parametrize(
    "fixture, exception",
    [
        ("not_in_library.vdf", AppNotInstalledError),
        ("in_library_but_bad_path.vdf", AppMovedError),
        ("malformed.vdf", VDFLoadError),
    ],
)
def test_not_in_library(monkeypatch, fixture, exception):
    import dzgui.api.steam as steam
    monkeypatch.setattr(steam, "LIBRARYFOLDERS_PATH", fixture)

    folder_path = Path(fixture_path("api"))
    with pytest.raises(exception):
        try:
            get_app_path(folder_path, APPID_DAYZ)
        except Exception as e:
            raise e


@pytest.fixture
def second_drive():
    return "in_library_on_second_drive.vdf"


def test_on_second_drive(monkeypatch, second_drive):
    import dzgui.api.steam as steam
    monkeypatch.setattr(steam, "LIBRARYFOLDERS_PATH", second_drive)
    folder_path = Path(fixture_path("api"))
    path = get_app_path(folder_path, APPID_DAYZ)
    assert path == Path("/tmp")
