from pathlib import Path
from typing import Callable, TYPE_CHECKING

from dzgui.api import pefile as PeFile

from dzgui.config import query
from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    APPNAME_DAYZ,
    APPNAME_DAYZ_EXP_HUMAN,
    NO_EXPAND,
    NO_FILL,
    NO_PADDING,
    VIEW_CONCEAL,
    VIEW_REVEAL,
)
from dzgui.const.endpoints import STEAM_API_SETUP
from dzgui.const.enum import Preferences, ServerTab
from dzgui.strings import options
from dzgui.util import strings, css, open_links

from dzgui.views.components.box import ShortHBox, VBox
from dzgui.views.components.eventbox import InfoEventBox
from dzgui.views.components.labels import LeftLabel
from dzgui.views.components.buttons import SpinnerButton, WebButton
from dzgui.views.components.frame import HeadingFrame
from dzgui.views.components.misc import ClientCombo, ErrorPopover
from dzgui.views.dialogs.generic import ExceptionDialog
from dzgui.views.mixins.scrollable_mixin import ScrollableMixin


import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter


class SubmitField(Gtk.Box):
    def __init__(
        self,
        controller: "Controller",
        placeholder: str,
        context: Preferences,
        slow: bool = False,
        private: bool = True,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.callback: Callable
        self.controller = controller
        self.context = context

        self.old_text: str
        self.placeholder = placeholder

        self.entry = Gtk.Entry(placeholder_text=placeholder, hexpand=True)

        # TODO: audit for all applicable callbacks
        if private:
            self.entry.set_icon_from_icon_name(
                Gtk.EntryIconPosition.SECONDARY, VIEW_REVEAL
            )
            self.entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
            self.entry.connect("icon-release", self._on_icon_release)
            self.entry.set_visibility(False)

        self.button: SpinnerButton | Gtk.Button
        if slow:
            self.button = SpinnerButton(label=options.save_button)
        else:
            self.button = Gtk.Button(label=options.save_button)

        self.button.connect("clicked", self._on_save_clicked)
        self.entry.connect("insert-text", self._on_text_typed)
        self.entry.connect("activate", self._on_field_activated)
        self.entry.get_property("buffer").connect("deleted-text", self._on_text_deleted)

        self.add(self.entry)
        self.add(self.button)

    def set_text(self, text: str) -> None:
        self.old_text = text
        self.entry.set_text(text)
        if len(text) == 0:
            self.button.set_sensitive(False)

    def _is_valid_text(self, text: str) -> bool:
        if text.isspace():
            return False
        if len(text) == 0:
            return False

        if text == self.old_text:
            return False
        return True

    def _on_text_deleted(
        self,
        buffer: Gtk.EntryBuffer,
        position: int,
        chars: int,
    ) -> None:

        text = buffer.get_text()
        state = self._is_valid_text(text)
        self.button.set_sensitive(state)

    def _on_text_typed(
        self,
        entry: Gtk.Entry,
        text: str,
        length: int,
        pos: int,
    ) -> None:

        buffer = entry.get_property("buffer")
        text = buffer.get_text() + text
        state = self._is_valid_text(text)
        self.button.set_sensitive(state)

    def _on_icon_release(
        self,
        widget: Gtk.Entry,
        icon_pos: Gtk.EntryIconPosition,
        event: Gdk.Event,
    ) -> None:
        visible = widget.get_visibility()
        if visible:
            icon, state = VIEW_REVEAL, False
        else:
            icon, state = VIEW_CONCEAL, True
        widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)
        widget.set_visibility(state)

    def _on_field_activated(self, entry: Gtk.Entry) -> None:
        text = entry.get_text()
        if not self._is_valid_text(text):
            return
        self.save_option()

    def set_callback(self, callback: Callable) -> None:
        self.callback = callback

    def save_option(self) -> None:
        self.callback()
        self.button.set_sensitive(False)

    def _on_save_clicked(self, button: Gtk.Button) -> None:
        self.save_option()


class SteamSubmitField(SubmitField):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(
            controller,
            options.steam_placeholder,
            Preferences.STEAM,
            slow=True,
            private=True,
        )

        self.pop = ErrorPopover(
            position=Gtk.PositionType.BOTTOM, relative_to=self.entry
        )
        self.pop.set_label(options.api_failed)
        self.pop.show_all()
        self.pop.popdown()

        emitter = controller.get_emitter()
        emitter.connect("api_change_failed", self._on_api_failure)
        emitter.connect("api_change_successful", self._on_api_success)

        self.set_callback(self.save_setting)

    def save_setting(self) -> None:
        self.entry.set_sensitive(False)
        text = "".join(self.entry.get_text().split())
        self.controller.update_steam_api_key(text)

    def _on_api_success(self, emitter: "Emitter") -> None:
        self.old_text = self.entry.get_text()
        if isinstance(self.button, SpinnerButton):
            self.button.stop_spinner()
        self.entry.set_sensitive(True)

    def _on_api_failure(self, emitter: "Emitter") -> None:
        self.pop.popup()
        if isinstance(self.button, SpinnerButton):
            self.button.stop_spinner()
        self.entry.set_sensitive(True)

    def block_text_entry(self) -> None:
        self.entry.set_position(-1)
        self.entry.set_can_focus(False)

    def unblock_text_entry(self) -> None:
        self.entry.set_can_focus(True)


class NameSubmitField(SubmitField):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(
            controller,
            options.name_placeholder,
            Preferences.NAME,
            private=False,
        )
        self.entry.set_width_chars(30)  # type: ignore
        self.set_callback(self.save_player_name)

    def save_player_name(self) -> None:
        value = self.entry.get_text().strip()
        self.old_text = value
        self.controller.update_config(self.context, value)


class ToggleField(Gtk.Box):
    def __init__(
        self,
        controller: "Controller",
        first_option: str,
        second_option: str,
        context: Preferences,
    ) -> None:
        super().__init__(spacing=5, halign=Gtk.Align.START)

        self.controller = controller
        self.context = context
        self.radio1 = Gtk.RadioButton.new_with_label(None, first_option)
        self.radio2 = Gtk.RadioButton.new_from_widget(self.radio1)
        self.radio2.set_label(second_option)
        self.pack_start(self.radio1, NO_EXPAND, NO_FILL, NO_PADDING)
        self.pack_start(self.radio2, NO_EXPAND, NO_FILL, NO_PADDING)

    def set_suboption_active(self, state: bool) -> None:
        # NOTE: defer connection of signal until after state is set
        self.radio2.set_active(state)
        self.radio1.connect("toggled", self._on_radio_toggled, self.context)

    def _on_radio_toggled(self, button: Gtk.RadioButton, context: Preferences) -> None:
        self.controller.toggle_config(context)

    def set_sensitive(self, state: bool) -> None:
        for el in self.radio1, self.radio2:
            el.set_sensitive(state)


class Options(ScrollableMixin, Gtk.ScrolledWindow):  # type: ignore
    def __init__(self, controller: "Controller"):
        super().__init__(
            margin_start=10,
            margin_end=10,
        )

        self.controller = controller
        self.controller.register_widget("options", self)

        self.DEFAULT_WIDTH = 1
        self.DEFAULT_HEIGHT = 1

        self.steam_entry: Gtk.Entry
        self.pop: Gtk.Popover

        self.steam = WebButton(label=strings.options.steam_web)
        self.steam.connect("clicked", self._on_link_button_clicked, STEAM_API_SETUP)

        self.steam_box = SteamSubmitField(controller)
        api_rows = [
            [LeftLabel(strings.options.steam_placeholder), self.steam_box, self.steam],
        ]

        self.player_box = NameSubmitField(controller)
        self.player_box.set_halign(Gtk.Align.START)
        self.player_box.get_children()[0].set_width_chars(30)  # type: ignore

        self.fullscreen_toggle = ToggleField(
            self.controller,
            strings.options.last_used,
            strings.options.always_fs,
            Preferences.WINDOW,
        )

        self.client_combo = ClientCombo()
        self.client_combo.connect("changed", self._on_client_changed)

        client_hbox = ShortHBox(self.client_combo)

        self.distance_toggle = ToggleField(
            self.controller, strings.options.km, strings.options.mi, Preferences.DIST
        )

        combo_store = Gtk.ListStore(str, object)
        tabs = (
            (options.server_combo, ServerTab.BROWSER),
            (options.saved_combo, ServerTab.SAVED),
            (options.recent_combo, ServerTab.RECENT),
            (options.lan_combo, ServerTab.LAN),
        )
        for tab in tabs:
            combo_store.append(tab)
        self.start_tab_combo = Gtk.ComboBox.new_with_model(combo_store)
        renderer_text = Gtk.CellRendererText()
        self.start_tab_combo.pack_start(renderer_text, True)
        self.start_tab_combo.add_attribute(renderer_text, "text", 0)
        self.start_tab_combo.set_active(0)

        start_tab_hbox = ShortHBox(self.start_tab_combo)
        self.start_tab_combo.connect("changed", self._on_start_tab_changed)

        pref_rows = [
            [LeftLabel(strings.options.client), client_hbox],
            [LeftLabel(strings.options.window_size), self.fullscreen_toggle],
            [LeftLabel(strings.options.distance), self.distance_toggle],
            [LeftLabel(options.start_tab), start_tab_hbox],
            [LeftLabel(strings.options.name), self.player_box],
        ]

        self.dayz_version_label = Gtk.Label(label=strings.null)
        self.dayz_exp_version_label = Gtk.Label(label=strings.null)

        version_rows = [
            [LeftLabel(APPNAME_DAYZ), self.dayz_version_label],
            [LeftLabel(APPNAME_DAYZ_EXP_HUMAN), self.dayz_exp_version_label],
        ]

        api_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        api_grid = self._make_grid(api_rows)
        api_box.add(api_grid)

        prefs_grid = self._make_grid(pref_rows)
        version_grid = self._make_grid(version_rows)

        col = 1
        row = 1
        grid = Gtk.Grid(
            orientation=Gtk.Orientation.VERTICAL,
            row_spacing=30,
            hexpand=True,
        )

        developers = Gtk.Button(label=options.developers, halign=Gtk.Align.START)
        developers.connect("clicked", self._on_developers_clicked)

        prefs = self.controller.get_prefs()
        if prefs.is_debug:
            grid.attach(developers, 1, 0, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)

        for pair in [
            (api_box, strings.options.api_key),
            (prefs_grid, strings.options.prefs),
            (version_grid, strings.options.version),
        ]:

            frame = HeadingFrame.new_with_widget_and_label(*pair)
            grid.attach(frame, col, row, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
            row += 1

        label = Gtk.Label(label=strings.options.header)
        label.set_halign(Gtk.Align.CENTER)
        css.add_class(label, "page-heading")

        box = VBox()
        box.add(label)
        box.add(grid)
        self.add(box)

        self.connect("key-press-event", self._on_keypress)

    def get_client_name(self) -> str:
        model = self.client_combo.get_model()
        ind = self.client_combo.get_active()
        return str(model[ind][0])

    def block_text_entry(self) -> None:
        self.steam_box.block_text_entry()
        # self.steam_entry.set_position(-1)
        # self.steam_entry.set_can_focus(False)

    def unblock_text_entry(self) -> None:
        self.steam_box.unblock_text_entry()
        # self.steam_entry.set_can_focus(True)

    def _on_developers_clicked(self, button: Gtk.Button) -> None:
        self.controller.show_developers_page()

    def _on_link_button_clicked(self, button: Gtk.Button, url: str) -> None:
        open_links.open_link_by_url(url)

    def _make_grid(self, rows: list) -> Gtk.Grid:
        grid = Gtk.Grid(
            orientation=Gtk.Orientation.VERTICAL,
            column_spacing=10,
            row_spacing=5,
            margin_start=5,
            margin_end=5,
            margin_top=10,
            margin_bottom=10,
        )
        row = 1
        for record in rows:
            col = 1
            for el in record:
                grid.attach(el, col, row, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
                col += 1
            row += 1
        return grid

    def _on_start_tab_changed(self, combo: Gtk.ComboBoxText) -> None:
        _iter = combo.get_active_iter()
        if _iter is None:
            raise ValueError(f"No active iterator set on {combo}")
        enum = combo.get_model()[_iter][1]
        index = enum.value
        self.controller.update_config(Preferences.START_TAB, index)

    def _on_client_changed(self, combo: Gtk.ComboBoxText) -> None:
        _iter = combo.get_active_iter()
        if _iter is None:
            raise ValueError(f"No active iterator set on {combo}")
        real_cmd = combo.get_model()[_iter][1]
        self.controller.update_config(Preferences.CLIENT, real_cmd)

    def populate_settings(self) -> None:
        prefs = self.controller.get_prefs()
        # NOTE: re-check in case file was removed by user between runs
        if prefs.paths.config.is_file() is False:
            dialog = ExceptionDialog(self.controller, strings.config_not_found)
            dialog.run()
            raise OSError(f"Config file '{prefs.paths.config}' not found")

        config = query.get_config(prefs.paths.config)

        # TODO: use newer config enums
        name = self.controller.query_config(Preferences.NAME)
        default_steam_path = self.controller.query_config(Preferences.DEFAULT)
        steam = self.controller.query_config(Preferences.STEAM)

        steam_path = Path(default_steam_path)

        self.steam_box.set_text(steam)
        self.player_box.set_text(name)

        fs = config["fullscreen"]
        miles = config["use_miles"]

        if prefs.is_steam_deck:
            self.fullscreen_toggle.set_sensitive(False)
            eb = InfoEventBox(options.fullscreen_eventbox, self.controller)
            self.fullscreen_toggle.add(eb)

            fs = True

        self.fullscreen_toggle.set_suboption_active(fs)
        self.distance_toggle.set_suboption_active(miles)

        dayz_version = PeFile.get_pretty_version(steam_path, APPID_DAYZ)
        if dayz_version is None:
            dayz_version = strings.null

        dayz_exp_version = PeFile.get_pretty_version(steam_path, APPID_DAYZ_EXP)
        if dayz_exp_version is None:
            dayz_exp_version = strings.null

        self.dayz_version_label.set_text(dayz_version)
        self.dayz_exp_version_label.set_text(dayz_exp_version)

        # TODO: bicolumn list store with no cell renderer on index 1, use raw command names
        active_combo = query.get_client_index(config["client"])
        self.client_combo.set_active(active_combo)

        start_tab = self.controller.query_config(Preferences.START_TAB)
        self.start_tab_combo.set_active(start_tab)

    def _suppress_toggles(self, state: bool) -> None:
        for toggle in [
            self.fullscreen_toggle,
            self.distance_toggle,
        ]:
            self.controller.suppress_signal(
                self, toggle.get_children()[0], "_on_radio_toggled", state
            )

    def _on_icon_release(
        self,
        widget: Gtk.Entry,
        icon_pos: Gtk.EntryIconPosition,
        event: Gdk.Event,
    ) -> None:
        visible = widget.get_visibility()
        if visible:
            icon, state = VIEW_REVEAL, False
        else:
            icon, state = VIEW_CONCEAL, True
        widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)
        widget.set_visibility(state)

    def grab_content_area(self) -> None:
        self.grab_focus()
