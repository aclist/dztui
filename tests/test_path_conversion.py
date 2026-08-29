from pathlib import Path
from dzgui.config.xdg import get_xdg_paths


def test_path_fallback(monkeypatch) -> None:
    envs = ["XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME"]
    for env in envs:
        monkeypatch.setenv(env, "/etc/dzgui")
    paths = get_xdg_paths()
    assert paths["XDG_CONFIG_HOME"] == Path.home().joinpath(".config/dzgui")
    assert paths["XDG_STATE_HOME"] == Path.home().joinpath(".local/state/dzgui")
    assert paths["XDG_DATA_HOME"] == Path.home().joinpath(".local/share/dzgui")
    assert paths["XDG_CACHE_HOME"] == Path.home().joinpath(".cache/dzgui")
