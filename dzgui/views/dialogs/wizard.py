import os
import textwrap

from enum import Enum
from importlib import resources
from pathlib import Path
from typing import Any, Callable, Self, TYPE_CHECKING

from dzgui.api.probe import test_steam_api, test_bm_api
from dzgui.api.shortcuts import add_steam_shortcut
from dzgui.api.steam import get_steam_paths
from dzgui.const.constants import (
    APP_NAME,
    APP_NAME_LOWER,
    HERO_PATH,
    LEGACY_CONFIG_PATH,
)
from dzgui.const.boilerplate import config_boilerplate
from dzgui.const.endpoints import BM_API_SETUP, STEAM_API_SETUP
from dzgui.const.enum import Preferences
from dzgui.config import freedesktop
from dzgui.config.query import lookup
from dzgui.init.migrate import migrate_legacy_conf
from dzgui.managers.threading import call_on_thread, StoredFunc, ThreadingManager
from dzgui.strings import wizard
from dzgui.util._json import write_json
from dzgui.util.open_links import open_link_by_url
from dzgui.util.css import add_class, load_css
from dzgui.views.components.buttons import WebButton
from dzgui.views.components.entry import APIEntry
from dzgui.views.components.misc import ClientCombo

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk, GLib, GObject, GdkPixbuf  # noqa E402

if TYPE_CHECKING:
    from dzgui.config.xdg import Xdg


class PageNum(Enum):
    INTRO = 1
    HAS_CONFIG = 2
    STEAM_PATH = 3
    STEAM_API = 4
    BM_API = 5
    USER_PREFS = 6
    SHORTCUTS = 7
    FINAL = 8

class OptionalPageMixin:
    """Marks optional pages as advanceable"""
    def _on_map(self, page: "ScrolledWizardPage") -> None:
        EMITTER.emit("step_complete")


class DescriptionArea(Gtk.Box):
    def __init__(self, text: str):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        wrapped = textwrap.fill(text, width=80)
        self.description = Gtk.Label(justify=Gtk.Justification.CENTER)
        self.description.set_markup(wrapped)
        self.add(self.description)


class Progress(Gtk.ProgressBar):
    def __init__(self) -> None:
        super().__init__(show_text=True)


class ScrolledWizardPage(Gtk.ScrolledWindow):
    def __init__(self, enum: PageNum, heading: str, description: str):
        super().__init__(overlay_scrolling=False)

        self.enum = enum
        self.page_type: Gtk.AssistantPageType
        self.title = heading
        self.heading = Heading(heading)
        self.description = DescriptionArea(description)

        hero = resources.files(APP_NAME_LOWER).joinpath(HERO_PATH)
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename=str(hero),
            width=600,
            height=600,
            preserve_aspect_ratio=True,
        )
        image = Gtk.Image.new_from_pixbuf(pixbuf)

        self.box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            margin_start=100,
            margin_end=100,
            margin_top=50,
            spacing=20,
        )

        self.add(self.box)
        self.prog = Progress()
        self.box.pack_end(self.prog, expand=False, fill=False, padding=0)
        self.box.pack_start(image, expand=False, fill=True, padding=0)
        self.box.pack_start(self.heading, expand=False, fill=True, padding=0)
        self.box.pack_start(self.description, expand=False, fill=True, padding=0)

        self.connect("map", self._on_map)

    def get_enum(self) -> PageNum:
        return self.enum

    def get_progress_bar(self) -> Progress:
        return self.prog

    def get_page_type(self) -> Gtk.AssistantPageType:
        return self.page_type

    def set_title(self, title: str) -> None:
        self.title = title

    def get_title(self) -> str:
        return self.title

    def add_start(self, content: Gtk.Widget) -> None:
        self.box.add(content)

    def add_end(self, content: Gtk.Widget) -> None:
        self.box.pack_end(content, expand=False, fill=False, padding=50)

    def get_box(self) -> Gtk.Box:
        return self.box

    def _on_map(self, page: "ScrolledWizardPage") -> None:
        pass


class NotificationFrame(Gtk.Frame):
    def __init__(self, label: str, error: bool = False) -> None:
        super().__init__(halign=Gtk.Align.CENTER)

        self.box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            margin_start=50,
            margin_end=50,
        )
        wrapped = textwrap.fill(label, width=80)
        self.label = Gtk.Label(
            label=wrapped,
            justify=Gtk.Justification.CENTER,
            margin_top=50,
            margin_bottom=50,
        )
        self.box.add(self.label)
        self.add(self.box)

        if error:
            add_class(self, "error-frame")

    def set_text(self, text: str) -> None:
        wrapped = textwrap.fill(text, width=80)
        self.label.set_markup(wrapped)


class APIValidationPage(ScrolledWizardPage):
    def __init__(
        self, enum: PageNum, heading: str, description: str, link: str, func: Callable
    ) -> None:
        super().__init__(
            enum=enum,
            heading=heading,
            description=description,
        )

        self.key = ""
        self.link = link
        self.thread_man = ThreadingManager(None)
        self.page_type = Gtk.AssistantPageType.INTRO

        self.validation_func = func

        self.validation_box = APIEntry()
        self.validation_box.set_halign(Gtk.Align.CENTER)
        self.validation_box.set_validation_func(self._pre_validate)

        self.link_button = WebButton(label=wizard.button_web_api)
        self.link_button.set_halign(Gtk.Align.CENTER)
        self.link_button.connect("clicked", self._on_link_clicked)

        self.spinner = Gtk.Spinner()
        self.success_box = NotificationFrame(wizard.api_success)

        self.add_start(self.link_button)
        self.add_start(self.validation_box)
        self.add_start(self.spinner)
        self.add_start(self.success_box)

        self.connect("map", lambda _: self.success_box.set_visible(False))

    def get_api_key(self) -> str:
        return self.key

    def _on_link_clicked(self, button: Gtk.Button) -> None:
        if self.link == "":
            return
        open_link_by_url(self.link)

    def _pre_validate(self, key: str) -> None:
        self.spinner.start()
        self.validation_box.disable_button()
        self.validation_func(key)

    def _cleanup(self, state: bool, key: str) -> None:
        if state:
            self.key = key
            self.validation_box.disable_button()
            self.success_box.set_visible(True)
            EMITTER.emit("step_complete")
        else:
            self.validation_box.popup()
            self.validation_box.enable_button()
        self.spinner.stop()


class BMValidationPage(OptionalPageMixin, APIValidationPage):
    def __init__(self) -> None:
        super().__init__(
            enum=PageNum.BM_API,
            heading=wizard.heading_bm_api,
            description=wizard.blurb_bm_api,
            link=BM_API_SETUP,
            func=self._validate,
        )
        self.connect("map", self._on_map)

    @call_on_thread("", show_dialog=False)
    def _validate(self, key: str) -> None:
        is_valid = test_bm_api(key.strip())
        cleanup = StoredFunc(self._cleanup, is_valid, key)
        self.thread_man.set_cleanup_func(cleanup)


class SteamValidationPage(APIValidationPage):
    def __init__(self) -> None:
        super().__init__(
            enum=PageNum.STEAM_API,
            heading=wizard.heading_steam_api,
            description=wizard.blurb_steam_api,
            link=STEAM_API_SETUP,
            func=self._validate,
        )

    @call_on_thread("", show_dialog=False)
    def _validate(self, key: str) -> None:
        is_valid = test_steam_api(key)
        cleanup = StoredFunc(self._cleanup, is_valid, key)
        self.thread_man.set_cleanup_func(cleanup)


class IntroductionPage(ScrolledWizardPage):
    def __init__(self) -> None:
        super().__init__(
            enum=PageNum.INTRO,
            heading=f"Welcome to {APP_NAME}!",
            description=wizard.blurb_intro,
        )
        self.page_type = Gtk.AssistantPageType.INTRO
        self.set_title(wizard.title_intro)


class Heading(Gtk.Label):
    def __init__(self, label: str):
        super().__init__(label=label)
        add_class(self, "settings-subheading")


class ChunkyButton(Gtk.Button):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.set_size_request(80, 80)

        wrapped = textwrap.fill(text, width=40)
        label = Gtk.Label(label=wrapped, justify=Gtk.Justification.CENTER)
        self.add(label)


class RadioFrame(Gtk.Frame):
    def __init__(
        self, parent: Gtk.RadioButton | None, button_path: tuple[Path, str]
    ) -> None:
        super().__init__()

        self.vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            margin_top=15,
            margin_start=10,
            margin_end=10,
            margin_bottom=15,
        )
        path, pretty = button_path
        if parent is None:
            self.button = Gtk.RadioButton.new_with_label(None, str(path))
        else:
            self.button = Gtk.RadioButton.new_with_label_from_widget(parent, str(path))
        self.vbox.add(self.button)
        label = Gtk.Label(halign=Gtk.Align.START)
        label.set_markup(pretty)
        self.vbox.add(label)
        self.add(self.vbox)

    def get_button(self) -> Gtk.RadioButton:
        return self.button


class ConfigMigrationPage(ScrolledWizardPage):
    def __init__(self, config: Path) -> None:
        super().__init__(
            enum=PageNum.HAS_CONFIG,
            heading=wizard.heading_config,
            description=wizard.blurb_config,
        )

        self.migrated = False
        self.config = config
        self.page_type = Gtk.AssistantPageType.INTRO

        self.import_button = ChunkyButton(wizard.config_import_button)
        self.new_button = ChunkyButton(wizard.config_new_button)

        self.grid = Gtk.Grid(column_spacing=30, halign=Gtk.Align.CENTER)
        self.grid.set_column_homogeneous(True)
        self.grid.attach(self.import_button, 0, 0, 1, 1)
        self.grid.attach(self.new_button, 1, 0, 1, 1)

        self.add_start(self.grid)

        self.err_box = NotificationFrame(wizard.config_error_box, error=True)
        self.success_box = NotificationFrame(wizard.config_import_box)
        self.from_scratch_box = NotificationFrame(wizard.config_new_box)
        for box in self.err_box, self.success_box, self.from_scratch_box:
            self.add_start(box)

        self.connect("map", self._hide_boxes)
        self.import_button.connect("clicked", self._on_import_clicked)
        self.new_button.connect("clicked", self._on_new_clicked)

    def _hide_boxes(self, page: Self) -> None:
        for box in self.success_box, self.from_scratch_box, self.err_box:
            box.set_visible(False)

    def _on_new_clicked(self, button: Gtk.Button) -> None:
        self.grid.set_sensitive(False)
        self.from_scratch_box.set_visible(True)
        EMITTER.emit("step_complete")
        EMITTER.emit("config", False)

    def is_migrated(self) -> bool:
        return self.migrated

    def _on_import_clicked(self, button: Gtk.Button) -> None:
        self.grid.set_sensitive(False)
        try:
            # TODO: this could be deferred to the final page (prevents accidental destruction of dialog via ESC)
            migrate_legacy_conf(self.config)
            self.migrated = True
            self.success_box.set_visible(True)
        except Exception:
            self.err_box.set_visible(True)
            EMITTER.emit("step_pending")
            return
        EMITTER.emit("step_complete")
        EMITTER.emit("config", True)


class PreferencesPage(ScrolledWizardPage):
    def __init__(self) -> None:
        super().__init__(
            enum=PageNum.USER_PREFS,
            heading=wizard.heading_prefs,
            description=wizard.blurb_prefs,
        )
        self.page_type = Gtk.AssistantPageType.INTRO

        # TODO: widgets and strings are largely a reimplementation of options page, consolidate
        name_label = Gtk.Label(label=wizard.label_player, halign=Gtk.Align.START)
        self.name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.name_entry = Gtk.Entry(
            placeholder_text=wizard.placeholder_player,
            halign=Gtk.Align.END,
            width_chars=40,
        )
        self.name_entry.connect("changed", self._on_entry_changed)
        self.name_box.add(name_label)
        self.name_box.add(self.name_entry)

        self.dist_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.radio_km = Gtk.RadioButton.new_with_label(None, wizard.radio_km)
        self.radio_miles = Gtk.RadioButton.new_with_label_from_widget(
            self.radio_km, wizard.radio_mi
        )
        dist_label = Gtk.Label(label=wizard.label_dist, halign=Gtk.Align.START)
        self.dist_box.add(dist_label)
        self.dist_box.add(self.radio_km)
        self.dist_box.add(self.radio_miles)

        client_label = Gtk.Label(label=wizard.label_client, halign=Gtk.Align.START)
        self.client_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.client_combo = ClientCombo()
        self.client_box.add(client_label)
        self.client_box.add(self.client_combo)

        outer_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER, spacing=10
        )
        for el in self.name_box, self.client_box, self.dist_box:
            outer_box.add(el)
        self.add_start(outer_box)

    def get_prefs(self) -> tuple[str, bool, str]:
        name = self.name_entry.get_text().strip()
        use_miles = self.radio_miles.get_active()
        model = self.client_combo.get_model()
        ind = self.client_combo.get_active()
        client = model[ind][1]
        return name, use_miles, client

    def _on_entry_changed(self, entry: Gtk.Entry) -> None:
        text = entry.get_text()
        if text.isspace():
            EMITTER.emit("step_pending")
            return
        EMITTER.emit("step_complete")


class CompletionPage(ScrolledWizardPage):
    def __init__(self) -> None:
        super().__init__(
            enum=PageNum.FINAL,
            heading=wizard.heading_completion,
            description=wizard.blurb_completion,
        )
        self.page_type = Gtk.AssistantPageType.SUMMARY

        self.connect("map", lambda _: EMITTER.emit("step_complete"))


class Assistant(Gtk.Assistant):
    def __init__(self, is_deck: bool, XDG: "Xdg"):
        super().__init__()
        if is_deck:
            self.fullscreen()
        else:
            self.set_default_size(1500, 900)

        self.is_binary = False if os.getenv("PYAPP") is None else True
        self.config_path = XDG.config

        self.config_values: dict[str, Any] = config_boilerplate

        self.setup_complete = False

        self.page1 = IntroductionPage()
        self.page2 = ConfigMigrationPage(XDG.config)
        self.page3 = SteamPathPage()
        self.page4 = SteamValidationPage()
        self.page5 = BMValidationPage()
        self.page6 = PreferencesPage()
        self.page7 = ShortcutCreationPage(XDG.shortcut)
        self.page8 = CompletionPage()

        self.set_forward_page_func(self._advance_page)

        EMITTER.connect("step_complete", self._mark_page_complete)
        EMITTER.connect("step_pending", self._mark_page_incomplete)
        EMITTER.connect("config", self._set_config_state)

        legacy_path = Path.home().joinpath(LEGACY_CONFIG_PATH)
        self.has_legacy_config = legacy_path.is_file()
        for page in (
            self.page1,
            self.page2,
            self.page3,
            self.page4,
            self.page5,
            self.page6,
            self.page7,
            self.page8,
        ):
            # NOTE: skip config migration page if no legacy config file
            if (
                isinstance(page, ConfigMigrationPage)
                and self.has_legacy_config is False
            ):
                continue
            # NOTE: disabled for now on system-provided packages
            if isinstance(page, ShortcutCreationPage) and not self.is_binary:
                continue
            self._add_page(page, page.get_page_type())

        self.connect("prepare", self._on_page_prepare)
        self.connect("cancel", self.destroy_and_quit)
        self.connect("close", self.destroy_and_quit)
        self.show_all()
        load_css()

    def write_config(self) -> None:
        write_json(self.config_values, self.config_path)

    def _advance_page(self, index: int) -> int:
        page = self.get_nth_page(index)
        match page:
            case IntroductionPage():
                pass
            case ConfigMigrationPage():
                if page.is_migrated():
                    steam_path = lookup(self.config_path, Preferences.DEFAULT)
                    self.page7.set_steam_path(steam_path)
                    offset = 1 if not self.is_binary else 2
                    self.setup_complete = True
                    return self.get_n_pages() - offset
            case SteamPathPage():
                self.config_values["default_steam_path"] = page.get_path_from_radio()
            case SteamValidationPage():
                self.config_values["steam_api"] = page.get_api_key()
            case BMValidationPage():
                self.config_values["bm_api"] = page.get_api_key()
            case PreferencesPage():
                # NOTE: collects config values before advancing to last page
                name, use_miles, client = self.page6.get_prefs()
                self.config_values["name"] = name
                self.config_values["use_miles"] = use_miles
                self.config_values["client"] = client
                self.write_config()
                self.page7.set_steam_path(self.config_values["default_steam_path"])
                self.setup_complete = True
            case ShortcutCreationPage():
                page.create_shortcuts()
            case _:
                raise AttributeError("Trying to advance a non-canonical page")
        return index + 1

    def is_setup_complete(self) -> bool:
        return self.setup_complete

    def destroy_and_quit(self, widget: Self) -> None:
        self.destroy()
        Gtk.main_quit()

    def _mark_page_incomplete(self, emitter: "Emitter") -> None:
        page_id = self.get_current_page()
        page = self.get_nth_page(page_id)
        if page is None:
            return
        self.set_page_complete(page, False)

    def _mark_page_complete(self, emitter: "Emitter") -> None:
        page_id = self.get_current_page()
        page = self.get_nth_page(page_id)
        if page is None:
            return
        self.set_page_complete(page, True)

    def _add_page(self, page: ScrolledWizardPage, ptype: Gtk.AssistantPageType) -> None:
        self.append_page(page)
        self.set_page_type(page, ptype)
        self.set_page_title(page, page.get_title())
        self.set_page_complete(page, True)

    def _set_config_state(self, emitter: "Emitter", state: bool) -> None:
        self.config = state

    def _on_page_prepare(self: Self, wizard: Self, page: ScrolledWizardPage) -> None:
        page_num = self.get_current_page() + 1
        total = self.get_n_pages()
        fraction = page_num / total

        bar = page.get_progress_bar()
        bar.set_fraction(fraction)
        bar.set_text(f"{page_num}/{total}")

        if not isinstance(page, IntroductionPage):
            EMITTER.emit("step_pending")


class CheckboxWithLabel(Gtk.Box):
    def __init__(self, text: str, blurb_text: str) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        self.button = Gtk.CheckButton(label=text)
        self.button.set_active(True)
        label = Gtk.Label(label="", halign=Gtk.Align.START, margin_start=20)
        wrapped = textwrap.fill(blurb_text, width=100)
        label.set_markup(f"- {wrapped}")

        for el in self.button, label:
            self.add(el)

    def get_checkbox(self) -> Gtk.CheckButton:
        return self.button

    def get_active(self) -> bool:
        return self.button.get_active()

    def set_active(self, state: bool) -> None:
        self.button.set_active(state)


class ShortcutCreationPage(OptionalPageMixin, ScrolledWizardPage):
    def __init__(self, shortcut: Path) -> None:
        super().__init__(
            enum=PageNum.SHORTCUTS,
            heading=wizard.heading_shortcuts,
            description=wizard.blurb_shortcuts,
        )

        self.steam_path: Path
        self.shortcut_path = shortcut
        self.checks_area = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=20
        )
        self.page_type = Gtk.AssistantPageType.INTRO

        label, blurb = wizard.checkbox_steam_shortcut
        self.steam_checkbox = CheckboxWithLabel(label, blurb)

        label, blurb = wizard.checkbox_start_menu
        self.start_menu_checkbox = CheckboxWithLabel(label, blurb)
        cb = self.start_menu_checkbox.get_checkbox()
        cb.connect("toggled", self._on_start_menu_toggled)

        label, blurb = wizard.checkbox_desktop_shortcut
        self.desktop_checkbox = CheckboxWithLabel(label, blurb)

        for el in (
            self.steam_checkbox,
            self.start_menu_checkbox,
            self.desktop_checkbox,
        ):
            self.checks_area.add(el)

        self.add_start(self.checks_area)
        self.show_all()
        self.connect("map", self._on_map)

    def _on_start_menu_toggled(self, button: Gtk.CheckButton) -> None:
        state = button.get_active()
        if not state:
            self.desktop_checkbox.set_active(state)
        self.desktop_checkbox.set_sensitive(state)

    def set_steam_path(self, path: Path) -> None:
        self.steam_path = path

    def create_shortcuts(self) -> None:
        # NOTE: best-effort, permissive even on failure (page is already marked as complete)
        if self.steam_checkbox.get_active():
            add_steam_shortcut(self.steam_path, self.shortcut_path)

        if self.start_menu_checkbox.get_active():
            desktop_file = freedesktop.write_desktop_file(self.shortcut_path)

        if self.desktop_checkbox.get_active():
            freedesktop.write_desktop_shortcut(desktop_file)


class SteamPathPage(ScrolledWizardPage):
    def __init__(self) -> None:
        super().__init__(
            enum=PageNum.USER_PREFS,
            heading=wizard.heading_steam_path,
            description=wizard.blurb_steam_path,
        )

        self.page_type = Gtk.AssistantPageType.INTRO
        self.err_box = NotificationFrame(wizard.no_valid_paths, error=True)

        self.scan_button = Gtk.Button(label=wizard.button_scan, halign=Gtk.Align.CENTER)
        self.scan_button.connect("clicked", self._on_scan_clicked)

        self.add_start(self.scan_button)
        self.add_start(self.err_box)
        self.connect("map", self._start_incomplete)

    def _on_scan_clicked(self, button: Gtk.Button) -> None:
        self.scan_button.set_sensitive(False)
        paths = get_steam_paths()

        button_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            halign=Gtk.Align.CENTER,
            spacing=10,
        )
        total = len(paths)
        if total == 0:
            show_errors = True
        else:
            button_box.add(Gtk.Label(label=f"Steam paths found: {total} total."))
            for i, button_path in enumerate(paths):
                if i == 0:
                    frame = RadioFrame(None, button_path)
                    self.first_button = frame.get_button()
                    button_box.add(frame)
                else:
                    frame = RadioFrame(self.first_button, button_path)
                    button_box.add(frame)
            self.add_start(button_box)
            show_errors = False
            EMITTER.emit("step_complete")
        self.show_all()
        # TODO: more robust approach
        self.err_box.set_visible(show_errors)

    def get_path_from_radio(self) -> str:
        active = next(r for r in self.first_button.get_group() if r.get_active())
        return active.get_label()

    def _start_incomplete(self, page: Self) -> None:
        self.err_box.set_visible(False)


class SetupWizard(Gtk.Application):
    def __init__(self, is_deck: bool, XDG: "Xdg") -> None:
        super().__init__()
        GLib.set_prgname(APP_NAME)
        self.win = Window(is_deck, XDG)
        Gtk.main()

    def is_setup_complete(self) -> int:
        return self.win.assistant.is_setup_complete()


class Window(Gtk.Window):
    def __init__(self, is_deck: bool, XDG: "Xdg") -> None:
        super().__init__(title=APP_NAME, icon_name=APP_NAME)
        self.assistant = Assistant(is_deck, XDG)


class Emitter(GObject.GObject):
    def __init__(self) -> None:
        super().__init__()

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def step_complete(self) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=())
    def step_pending(self) -> None:
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(bool,))
    def config(self, state: bool) -> None:
        pass


EMITTER = Emitter()
