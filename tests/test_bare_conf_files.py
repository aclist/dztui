import pytest
import tempfile

from dzgui.app_init import copy_bare_configs
from pathlib import Path

@pytest.mark.mods
def test_bare_file_import():
    conf_string = "DZGUI_CONF\n"
    state_string = "DZGUI_STATE\n"
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

    tmp = tempfile.TemporaryDirectory()
    tmp2 = tempfile.TemporaryDirectory()
    tmp_conf = Path(tmp.name)
    tmp_state = Path(tmp2.name)

    tmp_conf_file = tmp_conf / "config.json"
    tmp_conf_file.write_text(conf_string)
    for file in state:
        tmp_state.joinpath(file).write_text(state_string)

    tmp_state_file = tmp_state / "dzg.res.json"
    copy_bare_configs(tmp_conf_file, tmp_state_file)

    assert (tmp_conf / "dzgui/config.json").read_text() == conf_string
    for file in state:
       assert (tmp_state / "dzgui" / file).read_text() == state_string
