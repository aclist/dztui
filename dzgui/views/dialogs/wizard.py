import textwrap

from enum import Enum
from importlib import resources
from pathlib import Path
from typing import Any, Callable, Self

from dzgui.api.probe import test_steam_api, test_bm_api
from dzgui.api.steam import get_steam_paths
from dzgui.const.constants import (
    APP_NAME,
    APP_NAME_LOWER,
    HERO_PATH,
    LEGACY_CONFIG_PATH,
)
from dzgui.const.endpoints import BM_API_SETUP, STEAM_API_SETUP

from dzgui.init.migrate import migrate_legacy_conf
from dzgui.managers.threading import call_on_thread, StoredFunc, ThreadingManager
from dzgui.strings import wizard
from dzgui.util._json import write_json
from dzgui.util.open_links import open_link_by_url
from dzgui.util.css import add_class
from dzgui.views.components.buttons import WebButton
from dzgui.views.components.entry import APIEntry

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gtk, GLib, GObject, GdkPixbuf  # noqa E402


class PageNum(Enum):
    INTRO = 1
    HAS_CONFIG = 2
    STEAM_PATH = 3
    STEAM_API = 4
    BM_API = 5
    USER_PREFS = 6
    FINAL = 7


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
        super().__init__()

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
            # TODO: custom css file only for wizard
            add_class(self, "error-frame")


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


class BMValidationPage(APIValidationPage):
    def __init__(self) -> None:
        super().__init__(
            enum=PageNum.BM_API,
            heading=wizard.heading_bm_api,
            description=wizard.blurb_bm_api,
            link=BM_API_SETUP,
            func=self._validate,
        )

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
    def __init__(self, version: str):
        super().__init__(
            enum=PageNum.INTRO,
            heading=f"Welcome to {APP_NAME} {version}!",
            description=wizard.blurb_intro,
        )
        self.page_type = Gtk.AssistantPageType.INTRO
        self.set_title(wizard.title_intro)


class Heading(Gtk.Label):
    def __init__(self, label: str):
        super().__init__(label=label)

        # add_class(self, "heading")
        # font weight
        # TODO: set css em size
        # TODO: bold text


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

        self.success_box = NotificationFrame(wizard.config_import_box)
        self.from_scratch_box = NotificationFrame(wizard.config_new_box)
        self.add_start(self.success_box)
        self.add_start(self.from_scratch_box)

        self.connect("map", self._hide_boxes)
        self.import_button.connect("clicked", self._on_import_clicked)
        self.new_button.connect("clicked", self._on_new_clicked)

    def _hide_boxes(self, page: Self) -> None:
        for box in self.success_box, self.from_scratch_box:
            box.set_visible(False)

    def _on_new_clicked(self, button: Gtk.Button) -> None:
        self.grid.set_sensitive(False)
        self.from_scratch_box.set_visible(True)
        EMITTER.emit("step_complete")
        EMITTER.emit("config", False)

    def get_migrated(self) -> bool:
        return self.migrated

    def _on_import_clicked(self, button: Gtk.Button) -> None:
        self.grid.set_sensitive(False)
        try:
            migrate_legacy_conf(self.config)
            self.migrated = True
            self.success_box.set_visible(True)
        except Exception:
            pass
        EMITTER.emit("step_complete")
        EMITTER.emit("config", True)


class CompletionPage(ScrolledWizardPage):
    def __init__(self) -> None:
        super().__init__(
            enum=PageNum.FINAL,
            heading=wizard.heading_completion,
            description=wizard.blurb_completion,
        )
        # TODO: show collapsible config file tree
        self.page_type = Gtk.AssistantPageType.SUMMARY

        self.connect("map", lambda _: EMITTER.emit("step_complete"))


class Assistant(Gtk.Assistant):
    def __init__(self, version: str, is_deck: bool, config: Path):
        super().__init__()
        if is_deck:
            self.fullscreen()
        else:
            self.set_default_size(1500, 900)

        self.config_path = config
        # TODO: read in from boilerplate file
        from dzgui.const.boilerplate import config_boilerplate

        self.config_values: dict[str, Any] = config_boilerplate

        self.page1 = IntroductionPage(version)
        self.page2 = ConfigMigrationPage(config)
        self.page3 = SteamPathPage()
        self.page4 = SteamValidationPage()
        self.page5 = BMValidationPage()

        # self.page6 = PreferencesPage()
        # contains name, miles, and steam client choice
        # self.name = Gtk.Entry()
        # self.miles = Gtk.RadioButton()
        # TODO: use dual column model, recycle into options
        # TODO: update client_combo in options page
        # self.client = Gtk.ComboBox()
        # TODO: write to config if not present

        self.page7 = CompletionPage()

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
            self.page7,
        ):
            # NOTE: skip config migration page if no legacy config file
            if page == self.page2 and self.has_legacy_config is False:
                continue
            self._add_page(page, page.get_page_type())

        self.connect("prepare", self._on_page_prepare)
        self.connect("cancel", self.destroy_and_quit)
        self.connect("close", self.destroy_and_quit)
        self.show_all()

    def write_config(self) -> None:
        # NOTE: implies that file was already migrated on page 3
        if self.has_legacy_config:
            return
        write_json(self.config_values, self.config_path)

    def _advance_page(self, index: int) -> int:
        page = self.get_nth_page(index)
        match page:
            case self.page1:
                pass
            case self.page2:
                if self.page2.get_migrated():
                    return self.get_n_pages() - 1
            case self.page3:
                self.config_values["default_steam_path"] = page.get_path_from_radio()
            case self.page4:
                self.config_values["steam_api"] = page.get_api_key()
            case self.page5:
                self.config_values["bm_api"] = page.get_api_key()
            # case self.page6:
            # self.write_config()
            case _:
                raise AttributeError("Trying to advance a non-canonical page")
        print(self.config_values)
        return index + 1

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

        # NOTE: disable forward action
        if page != self.page1:
            EMITTER.emit("step_pending")


class SteamPathPage(ScrolledWizardPage):
    def __init__(self) -> None:
        super().__init__(
            enum=PageNum.USER_PREFS,
            heading=wizard.heading_steam_path,
            description=wizard.blurb_steam_path,
        )

        self.page_type = Gtk.AssistantPageType.INTRO

        # TODO: add custom CSS class to Gtk.Frame so that only this one is styled
        err_box = NotificationFrame(wizard.error_steam_path, error=True)
        self.err = err_box

        self.scan_button = Gtk.Button(label=wizard.button_scan, halign=Gtk.Align.CENTER)
        self.scan_button.connect("clicked", self._on_scan_clicked)

        self.add_start(self.scan_button)
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
        err_box = NotificationFrame(wizard.no_valid_paths)
        if total == 0:
            self.add_start(err_box)
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
            EMITTER.emit("step_complete")
        self.show_all()

    def get_path_from_radio(self) -> str:
        active = next(r for r in self.first_button.get_group() if r.get_active())
        return active.get_label()

    def _start_incomplete(self, page: Self) -> None:
        self.err.set_visible(False)

    def _test_error_func(self, button: Gtk.CheckButton) -> None:
        self.err.set_visible(True)
        EMITTER.emit("step_incomplete")


class SetupWizard(Gtk.Application):
    def __init__(self, version: str, is_deck: bool, config: Path) -> None:
        super().__init__()
        GLib.set_prgname(APP_NAME)
        Window(version, is_deck, config)
        Gtk.main()


class Window(Gtk.Window):
    def __init__(self, version: str, is_deck: bool, config: Path) -> None:
        super().__init__(title=APP_NAME, icon_name=APP_NAME)
        Assistant(version, is_deck, config)


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

# TODO: Ctrl-q
# TODO: change behavior of global emitter
