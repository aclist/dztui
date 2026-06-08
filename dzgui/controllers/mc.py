import logging
import threading

from typing import Any, TYPE_CHECKING, Union

import dzgui.util._json as JSON  # noqa


from dzgui.const.enum import (
    FilterMode,
    Preferences,
    NotebookPage,
    ButtonType,
    ContextMenu,
)

from dzgui.config.userprefs import UserPrefs
from dzgui.const.constants import APP_NAME
from dzgui.controllers.emitter import Emitter
from dzgui.managers.config import ConfigManager
from dzgui.managers.connection import ConnectionManager
from dzgui.managers.contextmenu import ContextMenuManager
from dzgui.managers.mods import ModManager
from dzgui.managers.notes import NoteManager
from dzgui.model.servers import ServerModelManager
from dzgui.util.diag import write_diagnostic
from dzgui.util.format import format_player_count
from dzgui.util.open_links import open_user_workshop, open_workshop_page
from dzgui.views.dialogs.filepicker import FilePicker, FolderPicker
from dzgui.views.dialogs.generic import ExceptionDialog

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject  # noqa E402

logger = logging.getLogger(APP_NAME)

if TYPE_CHECKING:
    from pathlib import Path
    from dzgui.api.servers import Record
    from dzgui.const.enum import ServerTab
    from dzgui.managers.connection import Prerequisites
    from dzgui.managers.filter import FilterManager
    from dzgui.util.dist import Haversine
    from dzgui.views.base import Notebook, Grid, OuterWindow
    from dzgui.views.components.buttonbox import ContextualButton
    from dzgui.views.components.filter_panel import FilterPanel
    from dzgui.views.components.right_panel import RightPanel
    from dzgui.views.components.statusbar import Statusbar
    from dzgui.views.pages.offline import OfflineLoader
    from dzgui.views.pages.options import Options
    from dzgui.views.pages.preconnect import PreConnectionAssistant
    from dzgui.views.pages.servers import ServerNotebook
    from dzgui.views.trees.tree_log import LogTreeView
    from dzgui.views.trees.tree_menu import MenuTreeView
    from dzgui.views.trees.tree_mods import ModTreeView
    from dzgui.views.trees.tree_servers import ServerTreeView


class AppNavigation:
    window: "OuterWindow"
    grid: "Grid"
    right_panel: "RightPanel"
    statusbar: "Statusbar"
    notebook: "Notebook"
    modtreeview: "ModTreeView"
    menu: "MenuTreeView"
    servers: "ServerNotebook"
    saved: "ServerTreeView"
    recent: "ServerTreeView"
    lan: "ServerTreeView"
    logtreeview: "LogTreeView"
    filters: "FilterPanel"
    preconnect: "PreConnectionAssistant"
    options: "Options"
    offline_loader: "OfflineLoader"


class Controller(GObject.GObject):
    def __init__(self) -> None:
        self.dist_cache: dict[str, "Haversine"] = {}
        self.mediator = AppNavigation()

        self.prefs: UserPrefs

        self.emitter = Emitter()
        self.emitter.connect("map_selection_changed", self._on_map_selection_changed)
        self.emitter.connect("check_toggled", self._on_check_toggled)

        # NOTE: suppress requests until entire UI is loaded
        self.loaded = False
        self.pending_jobs = 1

        self.exit_event = threading.Event()
        self.cancel_event = threading.Event()
        self.connection_man: ConnectionManager

    def get_emitter(self) -> Emitter:
        return self.emitter

    def register_widget(self, attr: str, widget: Gtk.Widget) -> None:
        try:
            setattr(self.mediator, attr, widget)
        except AttributeError:
            logger.critical(f"{attr} is not a valid AppNavigation attribute.")

    def get_prefs(self) -> UserPrefs:
        return self.prefs

    def set_prefs(self, prefs: UserPrefs) -> None:
        self.config_man = ConfigManager(prefs, self)
        self.notes_man = NoteManager(self, prefs.paths.notes)

        self.prefs = prefs

    def query_config(self, key: Preferences) -> Any:
        return self.config_man.lookup(key)

    def is_auto_install(self) -> bool:
        return bool(self.query_config(Preferences.INSTALL))

    def suppress_signal(
        self, owner: Any, child: Any, func_name: str, state: bool
    ) -> None:

        func = getattr(owner, func_name)
        if state:
            child.handler_block_by_func(func)
        else:
            child.handler_unblock_by_func(func)

    def get_active_context(self) -> "ServerTab":
        return self.get_active_treeview().get_enum()

    def get_active_treeview(self) -> "ServerTreeView":
        return self.mediator.notebook.servers.get_active_treeview()

    def grab_active_treeview(self) -> None:
        self.get_active_treeview().grab_focus()

    def save_res_and_quit(self, *args: Any) -> None:
        treeview = self.get_active_treeview()
        window = self.get_window()
        self.config_man.save_res_and_quit(treeview, window)

    def set_statusbar(self, enum: "NotebookPage | ServerTab", text: str) -> None:
        self.mediator.statusbar.set_by_context(enum, text)

    def remove_statusbar(self, context: "NotebookPage | ServerTab") -> None:
        self.mediator.statusbar.pop(context)

    def set_statusbar_dist(
        self, haversine: Union["Haversine", None], enum: "ServerTab"
    ) -> None:
        """
        NOTE: prevents race condition when server tab changed,
        but allows caching the distance in the background
        """
        context = self.get_active_context()
        page = self.mediator.notebook.get_page_by_enum()
        if page != NotebookPage.SERVERS:
            self.emitter.emit("distcalc_ended", None, context)
            return
        if enum != context:
            self.emitter.emit("distcalc_ended", None, context)
            return

        if haversine is None:
            self.emitter.emit("distcalc_ended", None, context)
            return
        dist = haversine.get_rounded(self.prefs.use_miles)
        self.emitter.emit("distcalc_ended", dist, context)

    def toggle_config(self, key: Preferences) -> None:
        # NOTE: Preferences.DIST is dynamic
        if key == Preferences.DIST:
            self.prefs.use_miles = not self.prefs.use_miles
        self.config_man.toggle_config(key)

    def update_config(self, key: Preferences, value: str) -> None:
        self.config_man.update_config(key, value)

    def open_keybindings(self) -> None:
        notebook = self.mediator.grid.notebook
        notebook.toggle_keybindings()

    def focus_notebook(self) -> None:
        notebook = self.mediator.grid.notebook
        notebook.focus_current()

    def show_developers_page(self) -> None:
        self.open_page(NotebookPage.DEVELOPERS)

    def open_page(self, page: NotebookPage) -> None:
        self.mediator.grid.notebook.set_page_by_enum(page)

    def open_page_by_button(self, button: "ContextualButton") -> None:
        # TODO: consolidate methods with set_page_by_enum
        match button.context:
            case ButtonType.EXIT:
                self.save_res_and_quit()
                return
            case ButtonType.OPTIONS:
                try:
                    # TODO: where to put config file check
                    self.mediator.grid.notebook.settings.populate_settings()
                except Exception:
                    return
            case ButtonType.MODS:
                self.load_mods()

        self.open_page(button.opens)

    def get_help_row(self) -> str:
        return self.mediator.menu.get_row_enum()

    def open_user_workshop(self, uid: str) -> None:
        # NOTE: uid may contain leading zeroes, not a real integer
        client = self.query_config(Preferences.CLIENT)
        open_user_workshop(uid, client)

    def load_mods(self) -> None:
        self.mod_man = ModManager(self)

    def uncolorize_mods(self) -> None:
        self.mod_man.uncolorize_mods()

    def highlight_stale(self) -> None:
        self.mod_man.highlight_stale()

    def toggle_mod_selection(self, state: bool) -> None:
        self.mod_man.toggle_mod_selection(state)

    def delete_mods(self) -> None:
        self.mod_man.delete_mods()

    def get_mod_store(self) -> Gtk.TreeModel | None:
        return self.mediator.modtreeview.get_model()

    def set_fav(self, name: str, record: str, simple_ip: str) -> None:
        try:
            self.config_man.set_fav(name, record)
            self.emitter.emit("fav_server_changed", name, simple_ip)
        except Exception as e:
            logger.critical(e)
            return

    def menu_action(self, action: ContextMenu, tree: "ServerTreeView") -> None:
        context_man = ContextMenuManager(tree, self)
        context_man.process(action)

    def populate_log(self) -> None:
        log = self.prefs.paths.debug
        try:
            self.mediator.logtreeview.populate_log(log)
            self.open_page(NotebookPage.LOG)
        except Exception as e:
            dialog = ExceptionDialog(self, str(e))
            dialog.run()

    def select_colorized(self) -> None:
        self.mod_man.select_colorized()

    def get_all_tree_filters(self) -> dict[str, dict[str, bool]]:
        servers = self.get_servers()
        all_filters: dict[str, dict[str, bool]] = {}
        trees = (
            servers.get_browser(),
            servers.get_saved(),
            servers.get_recent(),
            servers.get_lan(),
        )
        for tree in trees:
            enum = str(tree.get_enum())
            filters = tree.get_filter_man().get_filters()
            all_filters[enum] = filters
        return all_filters

    def get_filter_man(self) -> "FilterManager":
        """Each ServerTreeView has an atomic FilterManager"""
        return self.get_active_treeview().get_filter_man()

    def dump_diagnostics(self) -> None:
        picker = FilePicker(self.mediator.window)
        file = picker.pick_file()
        if file is not None:
            try:
                write_diagnostic(self.prefs.paths.config, file)
            except Exception as e:
                dialog = ExceptionDialog(self, str(e))
                dialog.run()

    def set_custom_folder(self) -> Union["Path", None]:
        picker = FolderPicker(self.mediator.window)
        return picker.pick_folder()

    def update_api_key(self, key: Preferences, text: str) -> None:
        self.config_man.update_api_key(key, text)

    def set_resolution(self, window: "OuterWindow") -> None:
        self.config_man.set_resolution(window)

    def propagate_column_width(self, col: Gtk.TreeViewColumn) -> None:
        GLib.idle_add(self.mediator.servers.update_tab_widths, col)

    def refresh_tree(self) -> None:
        treeview = self.get_active_treeview()
        treeview.set_loaded(False)
        ServerModelManager(self, treeview).refresh()

    def get_player_count(self) -> str:
        treeview = self.get_active_treeview()
        model, control = treeview.get_model_and_control_model()
        count = format_player_count(model, control)
        return count

    def get_statusbar(self) -> "Statusbar":
        return self.mediator.statusbar

    def populate_model(self, tv: "ServerTreeView") -> None:
        # NOTE: skip on previously loaded tabs
        if tv.is_loaded():
            self.emitter.emit("servers_loaded", tv.get_enum())
            return
        self.mediator.statusbar.set_by_context(tv.get_enum(), "")
        self.mediator.filters.button_grid.block_toggles(True)
        self.populate_filter_prefs()
        self.mediator.filters.button_grid.block_toggles(False)
        self.emitter.emit("lan_page_initialized")
        ServerModelManager(self, tv).load()

    def populate_filter_prefs(self) -> None:
        tv = self.get_active_treeview()
        filters = self.config_man.get_filters(tv)
        if filters is None:
            return
        filter_man = self.get_filter_man()
        for filt, state in filters.items():
            filter_man.set_filter(filt, state)
        self.mediator.filters.set_filters(filters)

    def get_dist_cache(self) -> dict[str, "Haversine"]:
        return self.dist_cache

    def set_dist_cache(self, addr: str, haversine: "Haversine") -> None:
        self.dist_cache[addr] = haversine

    def get_map_store(self) -> Gtk.ListStore:
        filter_man = self.get_filter_man()
        return filter_man.get_map_store()

    def get_enabled_filters(self) -> dict:
        filter_man = self.get_filter_man()
        return filter_man.get_filters()

    # FIXME: wipe maps store when changing tabs if model is none

    def has_server_model(self) -> bool:
        treeview = self.get_active_treeview()
        proxy_man = treeview.get_proxy_man()
        control = proxy_man.get_control()
        if control is None:
            return False
        if len(control) < 1:
            return False
        return True

    def _on_check_toggled(self, emitter: Emitter, label: str, state: bool) -> None:
        filter_man = self.get_filter_man()
        filter_man.set_filter(label, state)

        mode = FilterMode.TOGGLE_ON if state else FilterMode.TOGGLE_OFF
        ServerModelManager(self, self.get_active_treeview()).refilter(mode)

    def _on_map_selection_changed(self, emitter: Emitter, selection: str) -> None:
        smm = ServerModelManager(self, self.get_active_treeview())
        smm.refilter(FilterMode.TOGGLE_ON)

    def get_notebook(self) -> "Notebook":
        return self.mediator.notebook

    def get_prior_page(self) -> NotebookPage:
        return self.mediator.notebook.get_prior_page()

    def get_servers(self) -> "ServerNotebook":
        return self.mediator.servers

    def get_server_notebook(self) -> Gtk.Notebook:
        return self.mediator.servers.notebook

    def get_window(self) -> "OuterWindow":
        return self.mediator.window

    def get_menu(self) -> "MenuTreeView":
        return self.mediator.menu

    def has_favorites(self) -> bool:
        favs = self.config_man.get_favorites()
        if len(favs) < 1:
            return False
        return True

    def get_config_man(self) -> ConfigManager:
        return self.config_man

    def add_by_str(self, addr: str) -> None:
        saved_tree = self.get_servers().get_saved()
        ServerModelManager(self, saved_tree).add_by_str(addr)

    def add_by_record(self, record: "Record") -> None:
        saved_tree = self.get_servers().get_saved()
        ServerModelManager(self, saved_tree).add_by_record(record)

    def remove_by_record(self, record: "Record") -> None:
        saved_tree = self.get_servers().get_saved()
        ServerModelManager(self, saved_tree).remove_by_record(record)

    def add_to_history(self, row: dict[str, Any], record: "Record") -> None:
        tv = self.get_servers().get_recent()
        ServerModelManager(self, tv).add_to_history((row, record))

    # def append_to_history(self, record: "Record") -> None:
    #     self.config_man.append_to_history_file(record)

    def remove_from_history(self, record: "Record") -> None:
        # NOTE: remove action is only possible from history tree context menu,
        # i.e., the active tree
        tv = self.get_active_treeview()
        ServerModelManager(self, tv).remove_from_history(record)

    def connect_by_str(self, addr: str) -> None:
        if addr.isdigit():
            config_man = self.get_config_man()
            key = config_man.lookup(Preferences.BM)
            self.connection_man = ConnectionManager(self)
            self.connection_man.connect_by_id(int(addr), key)
        else:
            self.connection_man = ConnectionManager(self)
            self.connection_man.connect_by_ip(addr)

    def connect_by_record(self, record: "Record") -> None:
        self.connection_man = ConnectionManager(self)
        self.connection_man.connect_by_record(record)

    def get_details(self, record: "Record") -> None:
        ConnectionManager(self).query_details(record)

    def get_modlist(self, record: "Record") -> None:
        ConnectionManager(self).query_modlist_and_present(record)

    def get_server_name(self) -> str:
        tv = self.get_active_treeview()
        return tv.get_name()

    def open_workshop_page(self, mod: str) -> None:
        cmd = self.query_config(Preferences.CLIENT)
        open_workshop_page(mod, cmd)

    def has_note(self) -> bool:
        note = self.get_note()
        if len(note) > 0:
            return True
        return False

    def get_note_by_record(self, record: str) -> str:
        return self.notes_man.get_note(record)

    def get_note(self) -> str:
        tv = self.get_active_treeview()
        record = tv.get_record_string()
        return self.notes_man.get_note(record)

    def add_note(self, note: str) -> None:
        tv = self.get_active_treeview()
        record = tv.get_record_string()
        self.notes_man.add_note(record, note)

    def delete_note(self) -> None:
        tv = self.get_active_treeview()
        record = tv.get_record_string()
        self.notes_man.delete_note(record)

    def refresh_players(self, record: "Record") -> None:
        treeview = self.get_active_treeview()
        model, treeiter = treeview.get_selection().get_selected()
        ServerModelManager(self, treeview).update_playercount(treeiter, record)

    def get_active_keyword(self) -> str:
        return self.get_filter_man().get_active_keyword()

    def set_active_keyword(self, keyword: str) -> None:
        self.get_filter_man().set_active_keyword(keyword)

    def get_modtreeview(self) -> "ModTreeView":
        return self.mediator.modtreeview

    def get_exit_event(self) -> threading.Event:
        return self.exit_event

    def set_exit_event(self) -> None:
        self.exit_event.set()

    def set_cancel_event(self) -> None:
        self.cancel_event.set()

    def get_cancel_event(self) -> threading.Event:
        return self.cancel_event

    def clear_cancel_event(self) -> None:
        self.cancel_event.clear()

    def open_connection_assistant(self, prereqs: "Prerequisites") -> None:
        self.open_page(NotebookPage.CONNECTION)
        self.mediator.preconnect.populate(prereqs)

    def set_start_tab(self) -> None:
        ind = self.config_man.get_start_tab()
        self.get_servers().notebook.set_current_page(ind)

    def update_and_load_to_menu(self, raise_window: bool) -> None:
        self.connection_man.update_and_connect(raise_window, menu_only=True)

    def update_and_connect(self, raise_window: bool) -> None:
        self.connection_man.update_and_connect(raise_window)

    def update_status(self) -> None:
        self.mediator.preconnect.mark_finished()

    def get_steam_client_name(self) -> str:
        return self.mediator.options.get_client_name()

    def present_window(self) -> None:
        self.mediator.window.present_with_time(Gdk.CURRENT_TIME)

    def is_cancel_pending(self) -> bool:
        if self.get_exit_event().is_set():
            return True
        if self.get_cancel_event().is_set():
            self.clear_cancel_event()
            return True
        return False

    def open_offline(self, mods: Gtk.TreeModel | None) -> None:
        self.open_page(NotebookPage.OFFLINE)
        self.mediator.offline_loader.populate(mods)
