import pytest
import vdf

from dzgui.api.steam import AppNotInstalledError, get_app_path


@pytest.mark.parametrize("valid", [True, False])
def test_manifest_fallback_when_library_index_is_stale(tmp_path, valid):
    steam = tmp_path / "Steam"
    library = tmp_path / "Other library"
    (steam / "steamapps").mkdir(parents=True)
    (library / "steamapps/common/DayZ").mkdir(parents=True)
    (steam / "steamapps/libraryfolders.vdf").write_text(
        vdf.dumps({"libraryfolders": {"0": {"path": str(library), "apps": {}}}})
    )
    (library / "steamapps/appmanifest_221100.acf").write_text(
        vdf.dumps(
            {"AppState": {"appid": "221100" if valid else "123", "installdir": "DayZ"}}
        )
    )
    if valid:
        assert get_app_path(steam, 221100) == library
    else:
        with pytest.raises(AppNotInstalledError):
            get_app_path(steam, 221100)


def test_manifest_without_game_directory_is_rejected(tmp_path):
    (tmp_path / "steamapps").mkdir()
    (tmp_path / "steamapps/libraryfolders.vdf").write_text(
        vdf.dumps({"libraryfolders": {"0": {"path": str(tmp_path), "apps": {}}}})
    )
    (tmp_path / "steamapps/appmanifest_221100.acf").write_text(
        vdf.dumps({"AppState": {"appid": "221100", "installdir": "DayZ"}})
    )
    with pytest.raises(AppNotInstalledError):
        get_app_path(tmp_path, 221100)
