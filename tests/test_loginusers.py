import pytest

from pathlib import Path

from dzgui.api.steam import find_user_id
from tests.fixtures import fixture_path

pytestmark = pytest.mark.apitest


@pytest.mark.parametrize(
    "fixture, expect",
    [
        ("api/loginusers_legacy_client.vdf", 0),
        ("api/loginusers_legacy_client_multiple.vdf", 1),
        ("api/loginusers_beta_client.vdf", 0),
        ("api/loginusers_beta_client_multiple.vdf", 1),
        ("api/loginusers_beta_client_multiple_2.vdf", 0),
    ],
)
def test_loginusers(monkeypatch, fixture: str, expect: int) -> None:
    def mock_loginusers(path: Path) -> Path:
        return fixture_path(fixture)

    monkeypatch.setattr("dzgui.api.steam.find_loginusers", mock_loginusers)
    uid = find_user_id(Path(""))
    assert int(uid) == expect
