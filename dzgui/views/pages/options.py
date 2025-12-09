import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa

from pathlib import Path
from typing import TYPE_CHECKING

from dzgui.views.components.label import LeftLabel
from dzgui.views.components.eventbox import InfoEventBox
from dzgui.views.components.icon import Icon
from dzgui.views.components.web_button import WebButton
from dzgui.views.dialogs.link_dialog import WorkshopLinkDialog

from dzgui.util import strings, css, open_links
from dzgui.const.enum import Preferences, RowType, Popup
from dzgui.const.endpoints import STEAM_API_SETUP, BM_API_SETUP
from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    APPNAME_DAYZ,
    APPNAME_DAYZ_EXP,
    BETA_REPO,
    FLATPAK_RUN_CMD,
    FLATPAK_SANDBOX,
    NO_EXPAND,
    NO_FILL,
    STEAM_CMD,
    VIEW_CONCEAL,
    VIEW_REVEAL,
    )

from dzgui.config import query
from dzgui.api import pefile as PeFile
from dzgui.api.steam import find_user_id

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

class Options(Gtk.Box):
    def __init__(self, controller: "Controller"):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            margin_start=10,
            margin_end=10,
        )

        self.controller = controller

        self.DEFAULT_WIDTH = 1
        self.DEFAULT_HEIGHT = 1

        # TODO: strings
        label = Gtk.Label(label=strings.options.header)
        label.set_halign(Gtk.Align.CENTER)
        css.add_class(label, "page-heading")
        self.add(label)

        self.steam_entry = None
        self.bm_entry = None

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
        self.fullscreen_toggle = self.make_binary_radio(
            strings.options.last_used,
            strings.options.always_fs,
            Preferences.WINDOW,
        )

        self.client_combo = Gtk.ComboBoxText()
        # TODO: strings
        self.client_combo.append_text("Steam")
        self.client_combo.append_text("Flatpak")
        self.client_combo.append_text("Flatpak (container)")
        self.client_combo.set_active(0)
        self.client_combo.connect("changed", self._on_client_changed)
        hbox = Gtk.Box(spacing=5, halign=Gtk.Align.START)
        hbox.pack_start(self.client_combo, NO_EXPAND, NO_FILL, 0)

        self.distance_toggle = self.make_binary_radio(
            strings.options.km, strings.options.mi, Preferences.DIST
        )

        pref_rows = [
            [LeftLabel(strings.options.client), hbox],
            [LeftLabel(strings.options.window_size), self.fullscreen_toggle],
            [LeftLabel(strings.options.distance), self.distance_toggle],
            [LeftLabel(strings.options.name), self.player_box],
        ]

        self.mod_install_toggle = self.make_binary_radio(
            strings.options.manual_dl, strings.options.auto_dl, Preferences.INSTALL
        )
        self.force_button = Gtk.Button(label=strings.options.update)
        self.force_button.connect("clicked", self._on_force_update_clicked)

        # NOTE: sensitivity state is updated after config file is loaded
        self.force_button.set_sensitive(False)

        eb = InfoEventBox(strings.options.dl_eventbox, self)
        eb2 = InfoEventBox(strings.options.force_eventbox, self)

        mod_rows = [
            [LeftLabel(strings.options.install_mode), self.mod_install_toggle, eb],
            [LeftLabel(strings.options.force_update), self.force_button, eb2],
        ]

        self.dayz_version_label = Gtk.Label(label=strings.null)
        self.dayz_exp_version_label = Gtk.Label(label=strings.null)

        self.branch_combo = Gtk.ComboBoxText()
        self.branch_combo.append_text(strings.options.stable)
        self.branch_combo.append_text(strings.options.testing)
        self.branch_combo.set_active(0)
        self.branch_combo.connect("changed", self._on_branch_changed)
        self.branch_eb = InfoEventBox("", self)

        version_rows = [
            [LeftLabel(APPNAME_DAYZ), self.dayz_version_label],
            [LeftLabel(APPNAME_DAYZ_EXP), self.dayz_exp_version_label],
            [LeftLabel(strings.options.branch), self.branch_combo, self.branch_eb],
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
            spacing=10
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

        developers=Gtk.Button(label="Developers", halign=Gtk.Align.START)
        developers.connect("clicked", self._on_developers_clicked)
        if self.controller.get_developer_mode():
            grid.attach(
                developers, 1, 0, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT
            )

        for frame in [
            self.make_frame(api_box, strings.options.api_keys),
            self.make_frame(prefs_grid, strings.options.prefs),
            self.make_frame(mods_grid, strings.options.mods),
            self.make_frame(version_grid, strings.options.version),
        ]:
            grid.attach(
                frame, col, row, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT
            )
            row += 1

        self.scrollable = Gtk.ScrolledWindow(vexpand=True)
        self.scrollable.add(grid)
        self.add(self.scrollable)

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
            entry.set_icon_from_icon_name(
                Gtk.EntryIconPosition.SECONDARY, VIEW_REVEAL
            )
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
                grid.attach(
                    el, col, row, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT
                )
                col += 1
            row += 1
        return grid

    def _on_save_clicked(
        self, button: Gtk.Button, entry: Gtk.Entry, enum: Preferences
    ) -> None:
        old_text = self.controller.query_config(enum)
        button.set_sensitive(False)
        wait_msg = strings.dialog.working
        match enum:
            case Preferences.NAME:
                value = entry.get_text().strip()
                self.controller.update_config(enum, value)
            case Preferences.BM | Preferences.STEAM:
                text = "".join(entry.get_text().split())
                self.controller.set_callback(self.restore_api_text, old_text, entry)
                self.controller.update_api_key(text, enum)

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
        #wait_msg = strings.dialog.updating_mods
        #show_wait_dialog = True
        #call_on_thread(show_wait_dialog, cmd, wait_msg, "")

    def _on_client_changed(self, combo: Gtk.ComboBoxText) -> None:
        client = combo.get_active_text()
        match client:
            case "Steam":
                value = STEAM_CMD
            case "Flatpak":
                value = FLATPAK_RUN_CMD
            case "Flatpak (container)":
                value = FLATPAK_SANDBOX
        self.controller.update_config(Preferences.CLIENT, value)

    def _on_branch_changed(self, combo: Gtk.ComboBoxText) -> None:
        branch = combo.get_active_text()
        print("UNIMPLEMENTED")
        print(branch)
        ## TODO: needs to trigger download process
        #self.controller.toggle_branch(branch)
        #branch = combo.get_active_text().lower()
        #self.controller.update_config("branch", branch)
        #scripts/update

    def _on_radio_toggled(
        self, button: Gtk.RadioButton, context: Preferences
    ) -> None:
        AppNav = self.controller.get_mediator()

        state = button.get_group()[0].get_active()

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
                    self.uid
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
        hbox.pack_start(radio1, NO_EXPAND, NO_FILL, 0)
        hbox.pack_start(radio2, NO_EXPAND, NO_FILL, 0)

        return hbox

    def make_frame(self, widget: Gtk.Widget, text: str) -> Gtk.Box:
        label = Gtk.Label(label=text)
        label.set_halign(Gtk.Align.START)
        css.add_class(label, "settings-subheading")

        frame = Gtk.Frame(hexpand=True)
        frame.add(widget)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add(label)
        box.add(frame)

        return box

    def populate_settings(self) -> None:
        prefs = self.controller.get_prefs()
        if prefs.paths.config.is_file() is False:
            # in case file got deleted locally
            self.controller.spawn_dialog(strings.config_not_found, Popup.QUIT)
            return

        config = query.get_config(prefs.paths.config)
        name = config["name"]
        default_steam_path = config["default_steam_path"]
        steam = config["steam_api"]
        bm = config["bm_api"]
        install = config["auto_install"]

        steam_path = Path(default_steam_path)
        self.uid = find_user_id(steam_path)

        self.old_steam = steam
        self.old_bm = bm
        self.old_name = name

        self.steam_entry.set_text(steam)
        self.bm_entry.set_text(bm)
        self.player_box.get_children()[0].set_text(name)

        # NOTE: suppress toggle signal until radios are built
        self._suppress_toggles(True)
        self.force_button.set_sensitive(install)
        for el, conf_state in [
            (self.mod_install_toggle, install),
            (self.fullscreen_toggle, config["fullscreen"]),
            (self.distance_toggle, config["use_miles"])
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

        try:
            pe_file_path = PeFile.get_pefile_path(
                steam_path, APPID_DAYZ
            )
            vers = PeFile.get_dayz_version(pe_file_path)
            dayz_version = PeFile.dayz_version_to_str(vers)
        except Exception:
            dayz_version = strings.null

        try:
            exp_file_path = PeFile.get_pefile_path(
                steam_path, APPID_DAYZ_EXP
            )
            vers = PeFile.get_dayz_version(exp_file_path)
            dayz_exp_version = PeFile.dayz_version_to_str(vers)
        except Exception:
            dayz_exp_version = strings.null

        self.dayz_version_label.set_text(dayz_version)
        self.dayz_exp_version_label.set_text(dayz_exp_version)

        # TODO: not happy with this
        active_combo = query.get_client_index(config["client"])
        self.client_combo.set_active(active_combo)


        active_combo = 1 if config["branch"] == BETA_REPO else 0
        self.branch_combo.set_active(active_combo)
        self.branch_combo.set_sensitive(prefs.allow_updates)

        if prefs.allow_updates is True:
            msg = strings.options.self_update
        else:
            msg = strings.options.no_self_update
        self.branch_eb.set_text(msg)

    def _suppress_toggles(self, state: bool) -> None:
        for toggle in [
            self.mod_install_toggle,
            self.fullscreen_toggle,
            self.distance_toggle,
        ]:
            self.controller.suppress_signal(self, toggle.get_children()[0], "_on_radio_toggled", state)

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
