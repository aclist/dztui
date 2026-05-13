from pathlib import Path
from typing import TYPE_CHECKING

from dzgui.api import pefile as PeFile
from dzgui.api.steam import find_user_id
from dzgui.config import query
from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    APPNAME_DAYZ,
    APPNAME_DAYZ_EXP,
    FLATPAK_RUN_CMD,
    FLATPAK_SANDBOX,
    NO_EXPAND,
    NO_FILL,
    NO_PADDING,
    STEAM_CMD,
    VIEW_CONCEAL,
    VIEW_REVEAL,
)
from dzgui.const.endpoints import STEAM_API_SETUP, BM_API_SETUP
from dzgui.const.enum import Preferences, ServerTab
from dzgui.strings import errors, options
from dzgui.util import strings, css, open_links
from dzgui.views.components.buttons import SteamWorkshopButton
from dzgui.views.components.labels import LeftLabel
from dzgui.views.components.eventbox import InfoEventBox
from dzgui.views.components.buttons import WebButton
from dzgui.views.components.frame import HeadingFrame
from dzgui.views.dialogs.generic import ExceptionDialog
from dzgui.views.dialogs.link_dialog import WorkshopLinkDialog


import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter


class ShortHBox(Gtk.Box):
    def __init__(self, widget: Gtk.Widget) -> None:
        super().__init__(spacing=5, halign=Gtk.Align.START)

        self.pack_start(widget, NO_EXPAND, NO_FILL, NO_PADDING)


class Options(Gtk.Box):
    def __init__(self, controller: "Controller"):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            margin_start=10,
            margin_end=10,
        )

        self.controller = controller
        self.controller.register_widget("options", self)
        emitter = controller.get_emitter()
        emitter.connect("api_change_failed", self._on_api_change_failed)

        self.DEFAULT_WIDTH = 1
        self.DEFAULT_HEIGHT = 1

        label = Gtk.Label(label=strings.options.header)
        label.set_halign(Gtk.Align.CENTER)
        css.add_class(label, "page-heading")
        self.add(label)

        self.steam_entry: Gtk.Entry
        self.bm_entry: Gtk.Entry

        self.steam = WebButton(label=strings.options.steam_web)
        self.steam.connect("clicked", self._on_link_button_clicked, STEAM_API_SETUP)

        self.bm = WebButton(label=strings.options.bm_web)
        self.bm.connect("clicked", self._on_link_button_clicked, BM_API_SETUP)

        self.steam_box = self._make_submit_field(
            strings.options.enter_steam, Preferences.STEAM, True
        )
        self.bm_box = self._make_submit_field(
            strings.options.enter_bm, Preferences.BM, True
        )
        api_rows = [
            [LeftLabel(strings.options.steam_placeholder), self.steam_box],
            [LeftLabel(strings.options.bm_placeholder), self.bm_box],
        ]

        self.player_box = self._make_submit_field(
            strings.options.name_placeholder, Preferences.NAME
        )
        self.player_box.set_halign(Gtk.Align.START)
        # TODO: make submit field a standalone class
        self.player_box.get_children()[0].set_width_chars(30)

        self.fullscreen_toggle = self.make_binary_radio(
            strings.options.last_used,
            strings.options.always_fs,
            Preferences.WINDOW,
        )

        self.client_combo = Gtk.ComboBoxText()
        for text in (
            options.steam_combo,
            options.flatpak_combo,
            options.flatpak_container_combo,
        ):
            self.client_combo.append_text(text)
        self.client_combo.set_active(0)
        self.client_combo.connect("changed", self._on_client_changed)

        client_hbox = ShortHBox(self.client_combo)

        self.distance_toggle = self.make_binary_radio(
            strings.options.km, strings.options.mi, Preferences.DIST
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

        self.mod_install_toggle = self.make_binary_radio(
            strings.options.manual_dl, strings.options.auto_dl, Preferences.INSTALL
        )
        self.force_button = Gtk.Button(label=strings.options.update)
        self.force_button.connect("clicked", self._on_force_update_clicked)

        # NOTE: sensitivity state is updated after config file is loaded
        self.force_button.set_sensitive(False)

        eb = InfoEventBox(options.workshop_eventbox, controller)

        workshop_button = SteamWorkshopButton()  # label=strings.self_workshop)
        workshop_button.connect(
            "clicked", lambda _: self.controller.open_user_workshop(self.uid)
        )
        mod_rows = [
            [LeftLabel(options.workshop_label), workshop_button, eb],
        ]

        self.dayz_version_label = Gtk.Label(label=strings.null)
        self.dayz_exp_version_label = Gtk.Label(label=strings.null)

        version_rows = [
            [LeftLabel(APPNAME_DAYZ), self.dayz_version_label],
            [LeftLabel(APPNAME_DAYZ_EXP), self.dayz_exp_version_label],
        ]

        api_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        api_grid = self._make_grid(api_rows)
        api_box.add(api_grid)
        api_links_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            margin_start=5,
            margin_end=5,
            margin_top=5,
            margin_bottom=10,
            homogeneous=True,
            spacing=10,
        )
        api_links_box.add(self.steam)
        api_links_box.add(self.bm)
        api_box.add(api_links_box)

        prefs_grid = self._make_grid(pref_rows)
        mods_grid = self._make_grid(mod_rows)
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

        for frame in [
            HeadingFrame(api_box, strings.options.api_keys),
            HeadingFrame(prefs_grid, strings.options.prefs),
            HeadingFrame(mods_grid, strings.options.mods),
            HeadingFrame(version_grid, strings.options.version),
        ]:
            grid.attach(frame, col, row, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
            row += 1

        self.scrollable = Gtk.ScrolledWindow(vexpand=True)
        self.scrollable.add(grid)
        self.add(self.scrollable)

    def get_client_name(self) -> str:
        model = self.client_combo.get_model()
        ind = self.client_combo.get_active()
        return model[ind][0]

    def block_text_entry(self) -> None:
        for entry in self.steam_entry, self.bm_entry:
            entry.set_position(-1)
            entry.set_can_focus(False)

    def unblock_text_entry(self) -> None:
        for entry in self.steam_entry, self.bm_entry:
            entry.set_can_focus(True)

    def _on_developers_clicked(self, button: Gtk.Button) -> None:
        self.controller.show_developers_page()

    def _on_link_button_clicked(self, button: Gtk.Button, url: str) -> None:
        open_links.open_link_by_url(url)

    def _make_submit_field(
        self,
        placeholder: str,
        context: Preferences,
        private: bool = False,
    ) -> Gtk.Box:

        entry = Gtk.Entry(placeholder_text=placeholder, hexpand=True)
        button = Gtk.Button(label="Save")

        button.connect("clicked", self._on_save_clicked, entry, context)
        entry.connect("insert-text", self._on_text_typed, context, button)
        entry.connect("activate", self._on_field_activated, context, button)
        entry.get_property("buffer").connect(
            "deleted-text", self._on_text_deleted, context, button
        )

        if private:
            entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, VIEW_REVEAL)
            entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
            entry.connect("icon-release", self._on_icon_release)
            entry.set_visibility(False)

            if context == Preferences.STEAM:
                self.steam_entry = entry
            else:
                self.bm_entry = entry

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.add(entry)
        box.add(button)

        return box

    def _on_field_activated(
        self, entry: Gtk.Entry, context: Preferences, button: Gtk.Button
    ) -> None:
        text = entry.get_text()
        if not self._is_valid_text(text, context):
            return
        self._on_save_clicked(button, entry, context)

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

    def _on_save_clicked(
        self, button: Gtk.Button, entry: Gtk.Entry, enum: Preferences
    ) -> None:
        old_text = self.controller.query_config(enum)
        self.old_text = old_text
        self.old_entry = entry

        button.set_sensitive(False)
        match enum:
            case Preferences.NAME:
                value = entry.get_text().strip()
                self.controller.update_config(enum, value)
            case Preferences.BM | Preferences.STEAM:
                text = "".join(entry.get_text().split())
                self.controller.update_api_key(enum, text)

    def _on_api_change_failed(self, emitter: "Emitter") -> None:
        self.old_entry.set_text(self.old_text)
        dialog = ExceptionDialog(self.controller, errors.api_validation_error)
        dialog.run()

    def restore_api_text(self, text: str, entry: Gtk.Entry) -> None:
        entry.set_text(text)

    def revert(self, mode: Preferences) -> None:
        if mode == Preferences.STEAM:
            self.steam_entry.set_text(self.old_steam)
        else:
            self.bm_entry.set_text(self.old_bm)
        pass

    def _on_force_update_clicked(self, button: Gtk.Button) -> None:
        # TODO: unimplemented
        print("UNIMPLEMENTED")

    def _on_start_tab_changed(self, combo: Gtk.ComboBoxText) -> None:
        _iter = combo.get_active_iter()
        enum = combo.get_model()[_iter][1]
        index = enum.value
        self.controller.update_config(Preferences.START_TAB, index)

    def _on_client_changed(self, combo: Gtk.ComboBoxText) -> None:
        # TODO: use two columns or constants here, not strings
        client = combo.get_active_text()
        match client:
            case "Steam":
                value = STEAM_CMD
            case "Flatpak":
                value = FLATPAK_RUN_CMD
            case "Flatpak (container)":
                value = FLATPAK_SANDBOX
        self.controller.update_config(Preferences.CLIENT, value)

    def _on_radio_toggled(self, button: Gtk.RadioButton, context: Preferences) -> None:
        try:
            self.controller.toggle_config(context)
        except Exception:
            button.handler_block_by_func(self._on_radio_toggled)
            self.populate_settings()
            button.handler_unblock_by_func(self._on_radio_toggled)

        if context == Preferences.INSTALL:
            if self.controller.is_auto_install():
                self.force_button.set_sensitive(True)
                WorkshopLinkDialog(
                    self.controller,
                    strings.options.manual_sub_msg,
                    strings.self_workshop,
                    self.uid,
                )
            else:
                self.force_button.set_sensitive(False)

    def _is_valid_text(self, text: str, context: Preferences) -> bool:
        if text.isspace():
            return False
        if len(text) == 0:
            return False

        match context:
            case Preferences.NAME:
                old = self.old_name
            case Preferences.STEAM:
                old = self.old_steam
            case Preferences.BM:
                old = self.old_bm
        if text == old:
            return False
        return True

    def _on_text_deleted(
        self,
        buffer: Gtk.EntryBuffer,
        position: int,
        chars: int,
        context: Preferences,
        button: Gtk.Button,
    ) -> None:

        text = buffer.get_text()
        state = self._is_valid_text(text, context)
        button.set_sensitive(state)

    def _on_text_typed(
        self,
        entry: Gtk.Entry,
        text: str,
        length: int,
        pos: int,
        context: Preferences,
        button: Gtk.Button,
    ) -> None:

        buffer = entry.get_property("buffer")
        text = buffer.get_text() + text
        state = self._is_valid_text(text, context)
        button.set_sensitive(state)

    def make_binary_radio(
        self,
        first_option: str,
        second_option: str,
        context: Preferences,
    ) -> Gtk.Box:

        hbox = Gtk.Box(spacing=5, halign=Gtk.Align.START)
        radio1 = Gtk.RadioButton.new_with_label(None, first_option)
        radio2 = Gtk.RadioButton.new_from_widget(radio1)
        radio2.set_label(second_option)
        radio1.connect("toggled", self._on_radio_toggled, context)
        hbox.pack_start(radio1, NO_EXPAND, NO_FILL, NO_PADDING)
        hbox.pack_start(radio2, NO_EXPAND, NO_FILL, NO_PADDING)

        return hbox

    def populate_settings(self) -> None:
        prefs = self.controller.get_prefs()
        # NOTE: re-check in case file was removed by user between runs
        if prefs.paths.config.is_file() is False:
            dialog = ExceptionDialog(self.controller, strings.config_not_found)
            dialog.run()
            raise Exception

        config = query.get_config(prefs.paths.config)

        # TODO: use newer config enums
        name = config["name"]
        default_steam_path = config["default_steam_path"]
        steam = config["steam_api"]
        bm = config["bm_api"]
        install = config["auto_install"]

        steam_path = Path(default_steam_path)
        # NOTE: this is a best effort guess at the most recent user
        uid = find_user_id(steam_path)
        self.uid = "" if uid is None else uid

        self.old_steam = steam
        self.old_bm = bm
        self.old_name = name

        self.steam_entry.set_text(steam)
        self.bm_entry.set_text(bm)
        p = self.player_box.get_children()[0]
        if hasattr(p, "set_text"):
            p.set_text(name)

        # NOTE: suppress toggle signal until radios are built
        self._suppress_toggles(True)
        self.force_button.set_sensitive(install)
        for el, conf_state in [
            (self.mod_install_toggle, install),
            (self.fullscreen_toggle, config["fullscreen"]),
            (self.distance_toggle, config["use_miles"]),
        ]:
            el.get_children()[conf_state].set_active(True)
        self._suppress_toggles(False)

        # NOTE: disable buttons if no text is set
        for field in (
            [name, self.player_box],
            [steam, self.steam_box],
            [bm, self.bm_box],
        ):
            if field[0] == "":
                field[1].get_children()[1].set_sensitive(False)

        dayz_version = PeFile.get_pretty_version(steam_path, APPID_DAYZ)
        if dayz_version is None:
            dayz_version = strings.null

        dayz_exp_version = PeFile.get_pretty_version(steam_path, APPID_DAYZ_EXP)
        if dayz_exp_version is None:
            dayz_exp_version = strings.null

        self.dayz_version_label.set_text(dayz_version)
        self.dayz_exp_version_label.set_text(dayz_exp_version)

        # TODO: not happy with this
        active_combo = query.get_client_index(config["client"])
        self.client_combo.set_active(active_combo)
        # active_combo = 0

        start_tab = self.controller.query_config(Preferences.START_TAB)
        self.start_tab_combo.set_active(start_tab)

    def _suppress_toggles(self, state: bool) -> None:
        for toggle in [
            self.mod_install_toggle,
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
        return
