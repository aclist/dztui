import pytest
import tempfile
import os

from dzgui.app_init import copy_bare_configs
from dzgui.config.xdg import get_xdg_paths, parse_filepaths


CONF_STRING = "DZGUI_CONF\n"
STATE_STRING = "DZGUI_STATE\n"


@pytest.fixture
def state_files():
    state = [
        "dzg.history",
        "dzg.versions",
        "dzg.res.json",
        "dzg.filters.json",
        "dzg.columns.json",
        "dzg.notes.json",
        "ips.csv",
        ".month",
    ]
    return state


@pytest.fixture
def xdg_paths(monkeypatch):
    routes = {
        "XDG_CONFIG_HOME": "",
        "XDG_STATE_HOME": "",
        "XDG_DATA_HOME": "",
        "XDG_CACHE_HOME": "",
    }
    for route in routes:
        tmp = tempfile.TemporaryDirectory(delete=False)
        routes[route] = tmp.name
    for k, v in routes.items():
        monkeypatch.setenv(k, v)
    env = get_xdg_paths()
    return parse_filepaths(env)


@pytest.mark.mods
def test_config_file_import(xdg_paths, state_files):

    # NOTE: write bare files in root
    tmp_conf = xdg_paths.config.parent.parent
    tmp_conf_file = tmp_conf / xdg_paths.config.name
    tmp_conf_file.write_text(CONF_STRING)

    tmp_state = xdg_paths.resolution.parent.parent
    for file in state_files:
        tmp_state.joinpath(file).write_text(STATE_STRING)
    # NOTE: function should move files into "dzgui" subdirectory
    config_changed, state_changed = copy_bare_configs(
        xdg_paths.config, xdg_paths.resolution
    )

    assert xdg_paths.config.read_text() == CONF_STRING
    for file in state_files:
        expected = xdg_paths.resolution.parent.joinpath(file)
        assert expected.read_text() == STATE_STRING

    assert config_changed is True
    assert state_changed is True


@pytest.mark.mods
def test_config_file_no_import(xdg_paths, state_files):
    for subdir in xdg_paths.config.parent, xdg_paths.resolution.parent:
        subdir.mkdir()

    tmp_conf_file = xdg_paths.config
    tmp_conf_file.write_text(CONF_STRING)

    for file in state_files:
        xdg_paths.resolution.parent.joinpath(file).write_text(STATE_STRING)

    config_changed, state_changed = copy_bare_configs(
        xdg_paths.config, xdg_paths.resolution
    )
    assert config_changed is False
    assert state_changed is False
