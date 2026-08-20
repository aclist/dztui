import os
import subprocess

from pathlib import Path
from typing import Self, TYPE_CHECKING

from dzgui.api.shortcuts import Shortcuts
from dzgui.const.constants import APP_NAME
from dzgui.strings import uninstall
from dzgui.util._json import read_json
from dzgui.util.css import load_css
from dzgui.views.components.box import HBox
from dzgui.views.dialogs.wizard import ScrolledWizardPage, CheckboxWithLabel

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango  # noqa E402


class Assistant(Gtk.Assistant):
    def __init__(self, is_deck: bool, paths: dict[str, str]):
        super().__init__()
        if is_deck:
            # NOTE: deemed to be "safe" dimensions that exclude taskbar size
            self.set_default_size(1085, 670)
        else:
            self.set_default_size(1500, 900)

        self.set_forward_page_func(self._advance_page)

        pyapp = os.getenv("PYAPP")

        self.page1 = UninstallPage(paths, pyapp)
        self.page2 = CompletionPage(pyapp)

        self.append_page(self.page1)
        self.set_page_type(self.page1, Gtk.AssistantPageType.INTRO)
        self.set_page_title(self.page1, uninstall.pg1_title)
        self.set_page_complete(self.page1, True)

        self.append_page(self.page2)
        self.set_page_title(self.page2, uninstall.pg2_title)
        self.set_page_type(self.page2, Gtk.AssistantPageType.SUMMARY)

        self.connect("cancel", self.destroy_and_quit)
        self.connect("close", self.destroy_and_quit)
        self.show_all()
        load_css()

    def _advance_page(self, index: int) -> int:
        cur_page = self.get_nth_page(index)
        if cur_page == self.page1:
            self.page1.uninstall()
        return index + 1

    def destroy_and_quit(self, widget: Self) -> None:
        self.destroy()
        Gtk.main_quit()


class Window(Gtk.Window):
    def __init__(self, is_deck: bool, paths: dict[str, str]) -> None:
        super().__init__(title=APP_NAME, icon_name=APP_NAME)
        self.assistant = Assistant(is_deck, paths)


class CompletionPage(ScrolledWizardPage):
    def __init__(self, pyapp: str | None):
        super().__init__(heading=uninstall.pg2_heading, description=uninstall.pg2_blurb)

        text = (
            uninstall.standalone_uninstall
            if pyapp is not None
            else uninstall.system_uninstall
        )

        label = Gtk.Label(
            label=text,
            wrap_mode=Pango.WrapMode.WORD,
            margin=10,
            max_width_chars=80,
            justify=Gtk.Justification.CENTER,
        )
        frame = Gtk.Frame()
        frame.add(label)
        self.add_start(frame)


class FileLabel(HBox):
    def __init__(self, path: Path) -> None:
        super().__init__(spacing=10)

        label = Gtk.Label(label=uninstall.path_remove_prefix, halign=Gtk.Align.START)
        textview = Gtk.TextView(
            editable=False,
            halign=Gtk.Align.START,
            left_margin=10,
            right_margin=10,
        )
        textview.set_buffer(Gtk.TextBuffer(text=str(path)))
        self.extend([label, textview])


class CheckboxWithPath(CheckboxWithLabel):
    def __init__(
        self, label: str, details: str, path: Path, active: bool = True
    ) -> None:
        super().__init__(text=label, blurb_text=details)

        self.conf_path = path
        self.set_active(active)
        fl = FileLabel(path)
        self.indent_below(fl)

    def get_conf_path(self) -> Path:
        return self.conf_path


class UninstallPage(ScrolledWizardPage):
    def __init__(self, paths: dict[str, str], pyapp: str | None):
        super().__init__(heading=uninstall.pg1_heading, description=uninstall.pg1_blurb)

        self.pyapp = pyapp

        config = Path(paths["XDG_CONFIG_HOME"])
        state = Path(paths["XDG_STATE_HOME"])
        self.share = Path(paths["XDG_DATA_HOME"])
        shortcut = self.share.parent.joinpath("applications/dzgui.desktop")
        desktop = config.parent.parent.joinpath("Desktop/dzgui.desktop")
        self.steam_path = self.parse_steam_path(config, self.share)

        self.boxes: list[CheckboxWithPath] = []
        self.checks_area = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=20, margin_top=20
        )
        self.config_box = CheckboxWithPath(
            uninstall.config_label, uninstall.config_details, config, active=False
        )
        self.desktop_box = CheckboxWithPath(
            uninstall.desktop_label, uninstall.desktop_details, desktop
        )
        self.start_menu_box = CheckboxWithPath(
            uninstall.start_menu_label, uninstall.start_menu_details, shortcut
        )
        self.share_box = CheckboxWithPath(
            uninstall.desktop_label, uninstall.desktop_details, desktop
        )
        self.state_box = CheckboxWithPath(
            uninstall.state_label, uninstall.state_details, state
        )
        self.steam_box = CheckboxWithLabel(
            uninstall.steam_shortcut, uninstall.steam_details
        )

        for box in (
            self.config_box,
            self.state_box,
            self.desktop_box,
            self.start_menu_box,
        ):
            self.checks_area.add(box)
            self.boxes.append(box)

        self.checks_area.add(self.steam_box)

        self.add_start(self.checks_area)
        self.show_all()

    def parse_steam_path(self, config: Path, steam: Path) -> Path | None:
        try:
            file = config.joinpath("config.json")
            conf = read_json(file)
            steam = conf["default_steam_path"]
            self.steam_path = Path(steam)
            return Path(steam)
        except Exception as e:
            print(e)
            return None

    def wipe_conf_file(self, box: CheckboxWithPath) -> None:
        if box.get_active():
            path = box.get_conf_path()
            try:
                # TODO:
                # path.unlink()
                print(f"Deleted '{path}'")
            except Exception as e:
                print(e)

    def wipe_steam_shortcut(self) -> None:
        # TODO:
        pass
        # try:
        #     shortcuts = Shortcuts(self.steam_path)
        #     shortcuts.delete_shortcut(self.share)
        # except Exception as e:
        #     print(e)

    def wipe_pyapp(self) -> None:
        if self.pyapp is None:
            return
        res = subprocess.run([self.pyapp, "self", "remove"])
        print(res)

    def uninstall(self) -> None:
        for box in self.boxes:
            self.wipe_conf_file(box)
        if self.steam_box.get_active():
            self.wipe_steam_shortcut()
        # TODO:
        # self.wipe_pyapp()
        pass


class UninstallWizard(Gtk.Application):
    def __init__(self, is_deck: bool, paths: dict[str, str]) -> None:
        super().__init__()
        config = Path(paths["XDG_CONFIG_HOME"])
        # TODO: tests
        if not config.is_dir() or not config.joinpath("config.json").is_file():
            print(uninstall.not_installed)
            return
        GLib.set_prgname(APP_NAME)
        self.win = Window(is_deck, paths)
        Gtk.main()
