import pytest

from _pytest.monkeypatch import MonkeyPatch
from pathlib import Path

from dzgui.api.steam import get_app_allows_downloads
from tests.fixtures import fixture_path

pytestmark = pytest.mark.apitest


def mock_path(p: Path, appid: int) -> Path:
    return Path(fixture_path("api"))


def mock_config_allows(p: Path) -> Path:
    return Path(fixture_path("api/client_allows_downloads.vdf"))


def mock_config_disallows(p: Path) -> Path:
    return Path(fixture_path("api/client_disallows_downloads.vdf"))


def mock_config_missing(p: Path) -> Path:
    return Path(fixture_path(""))


@pytest.fixture
def client_allows() -> Path:
    return Path(fixture_path("api/client_allows_downloads.vdf"))


@pytest.fixture
def steam_path() -> Path:
    return Path(fixture_path("api"))


@pytest.fixture(scope="module", autouse=True)
def patch_api() -> None:
    mp = MonkeyPatch()
    mp.setattr("dzgui.api.steam.get_app_path", mock_path)
    yield
    mp.undo()


def test_app_allows_downloads(steam_path) -> None:
    assert get_app_allows_downloads(steam_path, 111) is True


def test_app_disallows_downloads(steam_path):
    assert get_app_allows_downloads(steam_path, 222) is False


def test_app_delegates_downloads(monkeypatch, steam_path, client_allows):
    monkeypatch.setattr("dzgui.api.steam.get_config", mock_config_disallows)
    assert get_app_allows_downloads(steam_path, 333) is False
    monkeypatch.setattr("dzgui.api.steam.get_config", mock_config_allows)
    assert get_app_allows_downloads(steam_path, 333) is True
    monkeypatch.setattr("dzgui.api.steam.get_config", mock_config_missing)
    assert get_app_allows_downloads(steam_path, 333) is True
