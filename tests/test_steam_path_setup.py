import json

import vdf
from types import SimpleNamespace
from unittest.mock import Mock, patch

from dzgui.views.dialogs.boot import BootDialog
from dzgui.views.dialogs.steam_path import Gtk, SteamPathDialog, SteamPathSelector


def make_selector(path):
    return SimpleNamespace(
        manual=Mock(get_active=Mock(return_value=True)),
        entry=Mock(get_text=Mock(return_value=str(path))),
        detected=Mock(),
        status=Mock(),
        changed=Mock(),
        valid_path="previous selection",
    )


def test_manual_path_validates_dayz_library(tmp_path):
    steam = tmp_path / "Steam with spaces"
    library = tmp_path / "DayZ library"
    library.mkdir()
    (steam / "steamapps").mkdir(parents=True)
    (steam / "steamapps/libraryfolders.vdf").write_text(
        vdf.dumps(
            {"libraryfolders": {"0": {"path": str(library), "apps": {"221100": "1"}}}}
        )
    )
    selector = make_selector(steam)
    SteamPathSelector._validate(selector)
    assert selector.valid_path == str(steam)
    selector.changed.assert_called_once_with(True)


def test_invalid_path_clears_previous_selection(tmp_path):
    selector = make_selector(tmp_path / "missing")
    SteamPathSelector._validate(selector)
    assert selector.valid_path == ""
    selector.changed.assert_called_once_with(False)


def test_library_without_dayz_is_rejected(tmp_path):
    (tmp_path / "steamapps").mkdir()
    (tmp_path / "steamapps/libraryfolders.vdf").write_text(
        vdf.dumps(
            {"libraryfolders": {"0": {"path": str(tmp_path), "apps": {"123": "1"}}}}
        )
    )
    selector = make_selector(tmp_path)
    SteamPathSelector._validate(selector)
    assert selector.valid_path == ""
    selector.changed.assert_called_once_with(False)


def test_save_preserves_other_preferences(tmp_path):
    config = tmp_path / "config.json"
    original = {
        "default_steam_path": "old",
        "steam_api": "test-key",
        "name": "Player",
        "ip_list": ["127.0.0.1:2302"],
    }
    config.write_text(json.dumps(original))
    dialog = SimpleNamespace(
        config=config,
        run=Mock(return_value=Gtk.ResponseType.OK),
        selector=SimpleNamespace(valid_path="new", _validate=Mock()),
        destroy=Mock(),
    )
    assert SteamPathDialog.save(dialog)
    assert json.loads(config.read_text()) == {**original, "default_steam_path": "new"}
    dialog.destroy.assert_called_once()


def test_cancel_keeps_configuration(tmp_path):
    config = tmp_path / "config.json"
    config.write_text('{"default_steam_path": "old"}')
    before = config.read_bytes()
    dialog = SimpleNamespace(
        config=config,
        run=Mock(return_value=Gtk.ResponseType.CANCEL),
        destroy=Mock(),
    )
    assert not SteamPathDialog.save(dialog)
    assert config.read_bytes() == before
    dialog.destroy.assert_called_once()


def test_recovery_restarts_boot_checks():
    boot = SimpleNamespace(
        xdg=SimpleNamespace(config="config.json"),
        failed=True,
        results=["stale result"],
        store=Mock(),
        boot_steps=["dayz", "symlinks"],
        error_box=Mock(),
        iter_step=Mock(),
    )
    with patch("dzgui.views.dialogs.boot.SteamPathDialog") as dialog:
        dialog.return_value.save.return_value = False
        BootDialog._on_reconfigure(boot, None)
        assert boot.failed
        boot.iter_step.assert_not_called()

        dialog.return_value.save.return_value = True
        BootDialog._on_reconfigure(boot, None)
    assert not boot.failed
    assert boot.results == []
    assert list(boot.steps) == boot.boot_steps
    boot.store.clear.assert_called_once()
    boot.iter_step.assert_called_once()
