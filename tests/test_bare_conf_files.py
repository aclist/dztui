import pytest
import tempfile

from dzgui.app_init import copy_bare_configs
from pathlib import Path

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
        ".month"
    ]
    return state

@pytest.mark.mods
def test_config_file_import(state_files):
    conf_string = "DZGUI_CONF\n"
    state_string = "DZGUI_STATE\n"

    tmp = tempfile.TemporaryDirectory()
    tmp2 = tempfile.TemporaryDirectory()
    tmp_conf = Path(tmp.name)
    tmp_state = Path(tmp2.name)

    tmp_conf_file = tmp_conf / "config.json"
    tmp_conf_file.write_text(conf_string)
    for file in state_files:
        tmp_state.joinpath(file).write_text(state_string)

    tmp_state_file = tmp_state / "dzg.res.json"
    config_changed, state_changed = copy_bare_configs(tmp_conf_file, tmp_state_file)

    assert (tmp_conf / "dzgui/config.json").read_text() == conf_string
    for file in state_files:
       assert (tmp_state / "dzgui" / file).read_text() == state_string

    assert config_changed is True
    assert state_changed is True

@pytest.mark.mods
def test_config_file_no_import(state_files):
    conf_string = "DZGUI_CONF\n"
    state_string = "DZGUI_STATE\n"

    tmp = tempfile.TemporaryDirectory()
    tmp2 = tempfile.TemporaryDirectory()
    tmp_conf = Path(tmp.name)
    tmp_state = Path(tmp2.name)

    for d in tmp_conf, tmp_state:
        subdir = d / "dzgui"
        subdir.mkdir()

    tmp_conf_file = tmp_conf / "dzgui/config.json"
    tmp_conf_file.write_text(conf_string)

    for file in state_files:
        tmp_state.joinpath("dzgui").joinpath(file).write_text(state_string)
    tmp_state_file = tmp_state / "dzgui/dzg.res.json"
    config_changed, state_changed = copy_bare_configs(tmp_conf_file, tmp_state_file)
    assert config_changed is False
    assert state_changed is False
