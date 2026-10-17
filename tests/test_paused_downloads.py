import pytest
from pathlib import Path

from dzgui.api.steam import is_dayz_downloading


@pytest.mark.parametrize(
    "file_list, expect",
    [
        (["state_221100_1111.patch"], True),
        (["state_736_1111.patch"], False),
        (["state_1024020_1111.patch"], True),
        (["221100"], False),
        (["221100", "state_221100_1111.patch"], True),
        (["state_221100_1111.patch", "state_1024020_1111.patch"], True),
        (["state_221100_1111"], False),
    ],
)
def test_dayz_patch_pending(monkeypatch, file_list, expect) -> None:
    def mock_get_pending_downloads(steam_path: Path, appid: int) -> None:
        files = [Path(file) for file in file_list]
        return files

    monkeypatch.setattr(
        "dzgui.api.steam.get_pending_downloads", mock_get_pending_downloads
    )
    assert is_dayz_downloading(Path("/tmp"), Path("/tmp")) == expect
