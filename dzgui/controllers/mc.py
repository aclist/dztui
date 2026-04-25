import inspect
import logging
import shutil
import threading

from functools import wraps
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING
from warnings import deprecated

import dzgui.api.pefile as PeFile
import dzgui.util._json as JSON  # noqa


from dzgui.api.mods import (
    get_delimited_mods,
    get_local_mod_path,
    find_stale_mods,
    _hash,
    remove_stale_signatures,
)
from dzgui.api.probe import test_steam_api, test_bm_api
from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    HEX_RED,
)
from dzgui.const.enum import (
    FilterMode,
    Preferences,
    NotebookPage,
    ButtonType,
    ContextMenu,
)

from dzgui.config.query import lookup
from dzgui.config.userprefs import UserPrefs
from dzgui.controllers.emitter import Emitter
from dzgui.managers.log import LogManager
from dzgui.managers.config import ConfigManager
from dzgui.managers.connection import ConnectionManager
from dzgui.managers.contextmenu import ContextMenuManager
from dzgui.managers.notes import NoteManager
from dzgui.model.proxy_model import ProxyModelManager
from dzgui.model.servers import ServerModelManager
from dzgui.model.model_factory import ModelFactory
from dzgui.util import strings
from dzgui.util.diag import write_diagnostic
from dzgui.util.format import format_mods, format_player_count
from dzgui.util.localize import number
from dzgui.util.open_links import open_user_workshop, open_workshop_page
from dzgui.views.dialogs.filepicker import FilePicker
from dzgui.views.dialogs.generic import ExceptionDialog, WaitDialog

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject  # noqa E402

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dzgui.api.servers import Record
    from dzgui.const.enum import ServerTab
    from dzgui.managers.filter_man import FilterManager
    from dzgui.util.dist import Haversine
    from dzgui.views.base import Notebook, Grid, OuterWindow
    from dzgui.views.components.buttonbox import ContextualButton
    from dzgui.views.components.filter_panel import FilterPanel
    from dzgui.views.components.right_panel import RightPanel
    from dzgui.views.components.statusbar import Statusbar
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


class StoredFunc:
    def __init__(self, func: Callable, *args, **kwargs) -> None:
        sig = inspect.signature(func)
        self.func = func
        self.bindings = sig.bind(*args, **kwargs)

    def call(self) -> None:
        self.func(*self.bindings.args, *self.bindings.kwargs)


class Controller(GObject.GObject):
    def __init__(self) -> None:
        self.dist_cache: dict[str, "Haversine", "ServerTab"] = {}
        self.mediator = AppNavigation()

        self.prefs: UserPrefs
        self.cleanup_func: StoredFunc = None

        self.emitter = Emitter()
        self.emitter.connect("map_selection_changed", self._on_map_selection_changed)
        self.emitter.connect("check_toggled", self._on_check_toggled)
        self.emitter.connect("servers_loaded_init", self._on_servers_loaded_init)

        # NOTE: suppress requests until entire UI is loaded
        self.loaded = False
        self.pending_jobs = 1

    def get_emitter(self) -> Emitter:
        return self.emitter

    def call_on_thread(dialog_str: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                def callback() -> None:
                    func(*args, **kwargs)
                    GLib.idle_add(self._destroy_on_idle)

                self = args[0]
                self.wait_dialog = WaitDialog(self, dialog_str, jobs=self.pending_jobs)
                self.wait_dialog.show_all()
                thread = threading.Thread(target=callback)
                thread.start()

            return wrapper

        return decorator

    def register_widget(self, attr: str, widget: Gtk.Widget) -> None:
        try:
            setattr(self.mediator, attr, widget)
        except AttributeError:
            logger.critical(f"{attr} is not a valid AppNavigation attribute.")

    def get_prefs(self) -> UserPrefs:
        # return self.config_man.get_prefs()
        return self.prefs

    def set_prefs(self, prefs: UserPrefs) -> None:
        self.config_man = ConfigManager(prefs)
        self.notes_man = NoteManager(self, prefs.paths.notes)
        self.prefs = prefs

    def query_config(self, key: Preferences) -> str | bool | list:
        return self.config_man.lookup(key)

    def is_auto_install(self) -> bool:
        return self.query_config(Preferences.INSTALL)

    def suppress_signal(
        self, owner: Gtk.Widget, widget: Gtk.Widget, func_name: str, state: bool
    ) -> None:

        func = getattr(owner, func_name)
        if state:
            widget.handler_block_by_func(func)
        else:
            widget.handler_unblock_by_func(func)

    def toggle_debug_mode(self) -> None:
        self.toggle_config(Preferences.DEBUG)

    def get_active_context(self) -> Gtk.TreeView:
        return self.get_active_treeview().get_enum()

    def get_active_treeview(self) -> "ServerTreeView":
        return self.mediator.notebook.servers.get_active_treeview()

    def grab_active_treeview(self) -> None:
        self.get_active_treeview().grab_focus()

    def save_res_and_quit(self, *args: Any) -> None:
        treeview = self.get_active_treeview()
        window = self.get_window()
        self.config_man.save_res_and_quit(treeview, window)

    @deprecated("use statusbar internal contexts")
    def remove_statusbar(self, context: str) -> None:
        c = self.mediator.statusbar.statusbar.get_context_id(context)
        self.mediator.statusbar.statusbar.pop(c)

    # TODO: refactor any modules using this
    # cf. eventbox.py
    @deprecated("use set_by_context")
    def set_statusbar(self, text: str, context: str) -> int:
        msg_id = self.mediator.statusbar.set_text(text, context)
        return msg_id

    # TODO: StatusBarManager
    def set_statusbar_dist(self, haversine: "Haversine", enum: "ServerTab") -> None:
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

        dist: str
        if haversine is None:
            dist = "Unknown"
        else:
            if self.prefs.use_miles:
                raw = round(haversine.as_miles())
                separated = number(raw)
                dist = str(separated) + " mi"
            else:
                raw = round(haversine.as_kilometers())
                separated = number(raw)
                dist = str(separated) + " km"

        self.emitter.emit("distcalc_ended", dist, context)

    def delete_multiple_mods(self) -> None:
        sel = self.mediator.modtreeview.get_selection()
        model, pathlist = sel.get_selected_rows()
        # NOTE: reverse when multiple selection
        for path in reversed(pathlist):
            self.delete_single_mod(path)

        total_mods, total_size = self.calc_mod_size()
        self.update_mod_statusbar()

    def load_mods_cleanup(self, model: Gtk.ListStore) -> None:
        self.mediator.modtreeview.set_model(model)
        self.emitter.emit("mod_page_loaded")

    # TODO: delegate to threadmanager
    @call_on_thread(strings.dialog.modlist)
    def load_mods(self) -> None:
        model = ModelFactory().make_mod_store()
        path = self.query_config(Preferences.DEFAULT)
        mods = get_delimited_mods(Path(path))
        model.extend(mods)

        self.cleanup_func = StoredFunc(self.load_mods_cleanup, model)

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
                # TODO: reload using refresh button, rather than on demand?
                self.load_mods()

        self.open_page(button.opens)

    def get_help_row(self) -> str:
        return self.mediator.menu.get_row_enum()

    def open_user_workshop(self, uid: str) -> None:
        # NOTE: uid may contain leading zeroes, not a real integer
        client = self.query_config(Preferences.CLIENT)
        open_user_workshop(uid, client)

    def delete_single_mod_cleanup(self, _iter: Gtk.TreeIter) -> None:
        self.get_mod_store().remove(_iter)
        remove_stale_signatures(self.prefs.paths.config, self.prefs.paths.version)

    # TODO: strings
    # TODO: delegate to LocalModManager or api/mods.py
    @call_on_thread("deleting mod")
    def delete_single_mod(self, tree_path: Gtk.TreePath) -> None:
        config = self.prefs.paths.config
        mod, _iter = self.get_mod_from_tree_path(tree_path)

        path = lookup(config, Preferences.DEFAULT)
        steam_path = Path(path)
        mods_path = get_local_mod_path(steam_path)
        app_path = PeFile.get_nested_app_path(steam_path, APPID_DAYZ)

        md5 = _hash(mod)
        symlink = app_path / md5
        symlink.unlink()
        shutil.rmtree(mods_path / mod)

        # NOTE: second pass to unlink DAYZ_EXP mods
        # TODO: test this with working APPID_DAYZ_EXP installation
        try:
            app_path_exp = PeFile.get_nested_app_path(steam_path, APPID_DAYZ_EXP)
            symlink = app_path_exp / md5
            symlink.unlink()
        except PeFile.AppNotInstalledError:
            pass

        self.cleanup_func = StoredFunc(self.delete_single_mod_cleanup, _iter)

    def get_mod_store(self) -> Gtk.ListStore:
        return self.mediator.modtreeview.get_model()

    def format_mod_statusbar(self) -> str:
        total_mods, total_size = self.calc_mod_size()
        msg = format_mods(total_size, total_mods)
        return msg

    def calc_mod_size(self) -> tuple[int, int]:
        model = self.get_mod_store()
        if model is None:
            return 0, 0
        total_mods = len(model)
        total_size = 0
        for mod in model:
            total_size += mod[3]
        return total_mods, total_size

    def set_fav(self) -> None:
        treeview = self.get_active_treeview()
        name = treeview.get_value_at_index(0)
        record = treeview.get_record_string()

        try:
            self.config_man.write_config(Preferences.FAV_LBL, name)
            self.config_man.write_config(Preferences.FAV_SRV, record)
        except Exception as e:
            logger.critical(e)
            # TODO: add a failure dialog here
            return

        simple_ip = treeview.get_simplified_ip()
        self.emitter.emit("fav_server_changed", name, simple_ip)

    def menu_action(self, action: ContextMenu, tree: Gtk.TreeView) -> None:
        context_man = ContextMenuManager(tree, self)
        context_man.process(action)

    def toggle_mod_selection(self, state: bool) -> None:
        sel = self.mediator.modtreeview.get_selection()
        if state:
            sel.select_all()
        else:
            sel.unselect_all()
        # TODO: signal
        self.mediator.modtreeview.grab_focus()

    def populate_log(self) -> None:
        log = self.prefs.paths.debug
        try:
            self.mediator.logtreeview.populate_log(log)
            self.open_page(NotebookPage.LOG)
        except Exception as e:
            dialog = ExceptionDialog(self, str(e))
            dialog.run()

    def select_colorized(self) -> None:
        model = self.get_mod_store()
        sel = self.mediator.modtreeview.get_selection()
        for mod in model:
            it = mod.iter
            path = model.get_path(it)
            if mod[4] == HEX_RED:
                sel.select_path(path)

    # TODO: make as method of tree?
    # TODO: could have a LocalModManager that accepts button enums
    def uncolorize_mods(self) -> None:
        model = self.get_mod_store()
        for mod in model:
            it = mod.iter
            path = model.get_path(it)
            model[path][4] = None
        self.mediator.modtreeview.set_cursor(0)

    def get_filter_man(self) -> "FilterManager":
        """Each ServerTreeView has an atomic FilterManager"""
        return self.get_active_treeview().get_filter_man()

    def highlight_stale_cleanup(self, stale_mods: list) -> None:
        """Manipulates attached ListStore in the main event loop"""
        model = self.get_mod_store()
        for mod in model:
            it = mod.iter
            path = model.get_path(it)
            if int(mod[2]) in stale_mods:
                model[path][4] = True
        self.emitter.emit("mods_highlighted")

    # TODO: delegate to mod manager
    @call_on_thread(strings.dialog.working)
    def highlight_stale(self) -> None:
        # TODO: set progress bar for number of mods
        stale = find_stale_mods(self.prefs.paths.config)
        self.cleanup_func = StoredFunc(self.highlight_stale_cleanup, stale)

    def set_cleanup_func(self, func: StoredFunc) -> None:
        self.cleanup_func = func

    def get_cleanup_func(self) -> StoredFunc:
        return self.cleanup_func

    def _destroy_on_idle(self) -> None:
        self.wait_dialog.destroy()
        func = self.get_cleanup_func()
        if func is not None:
            func.call()
            self.set_cleanup_func(None)
        self.mediator.window.set_sensitive(True)

    def dump_diagnostics(self) -> None:
        picker = FilePicker(self.mediator.window)
        file = picker.pick_file()
        if file is not None:
            try:
                write_diagnostic(self.prefs.paths.config, file)
            except Exception as e:
                dialog = ExceptionDialog(self, str(e))
                dialog.run()

    # TODO: move to ConfigMan
    @call_on_thread(strings.dialog.working)
    def update_api_key(self, text: str, key: Preferences) -> None:
        if key is Preferences.STEAM:
            res = test_steam_api(text)
        else:
            res = test_bm_api(text)

        if res is True:
            self.update_config(key, text)
        else:
            self.cleanup_func = StoredFunc(
                lambda: self.emitter.emit("api_change_failed")
            )

    def set_resolution(self, window: "OuterWindow") -> None:
        self.config_man.set_resolution(window)

    def propagate_column_width(self, col: Gtk.TreeViewColumn) -> None:
        GLib.idle_add(self.mediator.servers.update_tab_widths, col)

    def refresh_tree(self) -> None:
        treeview = self.get_active_treeview()
        treeview.set_loaded(False)
        ServerModelManager(self, treeview).refresh()

    # TODO: move to servermodelman
    def get_player_count(self) -> str:
        treeview = self.get_active_treeview()
        model = treeview.get_model()
        proxy_man = treeview.get_proxy_man()
        control_model = proxy_man.get_control()
        count = format_player_count(model, control_model)
        return count

    def get_statusbar(self) -> "Statusbar":
        return self.mediator.statusbar

    def get_proxy_man(self) -> "ProxyModelManager":
        return self.proxy_man

    def populate_model(self, tv: "ServerTreeView") -> None:
        # NOTE: skip on previously loaded tabs
        if tv.is_loaded():
            self.emitter.emit("servers_loaded", tv.get_enum())
            return
        # TODO: placeholder logic, wipe statusbar when changing page
        self.mediator.statusbar.set_text("", "")
        ServerModelManager(self, tv).load()

    def get_dist_cache(self) -> dict[str, "Haversine", "ServerTab"]:
        return self.dist_cache

    def get_filters(self) -> list:
        return self.mediator.filters.get_filters()

    # TODO: clean up routes between controller and filter panel
    def get_map_store(self) -> Gtk.ListStore:
        filter_man = self.get_filter_man()
        return filter_man.get_map_store()

    def get_selected_map(self) -> str:
        filter_man = self.get_filter_man()
        return filter_man.get_selected_map()

    def get_enabled_filters(self) -> dict:
        filter_man = self.get_filter_man()
        return filter_man.get_filters()

    # TODO: rename
    def _on_servers_loaded_init(self, emitter: "Emitter") -> None:
        """Triggered after servers load but prior to maps loading"""
        # FIXME: wipe maps store when changing tabs if model is none
        tv = self.get_active_treeview()
        if tv.loaded is False:
            return
        store = self.get_map_store()
        self.emitter.emit("load_maps", store)

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
        smm.refilter(FilterMode.MAP)

    def get_notebook(self) -> "Notebook":
        return self.mediator.notebook

    def get_prior_page(self) -> NotebookPage:
        return self.mediator.notebook.get_prior_page()

    def get_servers(self) -> "ServerNotebook":
        return self.mediator.servers

    def get_server_notebook(self) -> "Notebook":
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

    def is_in_favs(self) -> bool:
        return self.config_man.is_in_favs()

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

    def connect_by_str(self, addr: str) -> None:
        if addr.isdigit():
            config_man = self.get_config_man()
            key = config_man.lookup(Preferences.BM)
            ConnectionManager(self).connect_by_id(addr, key)
        else:
            ConnectionManager(self).connect_by_ip(addr)

    def connect_by_record(self, record: "Record") -> None:
        ConnectionManager(self).connect_by_record(record)

    def get_details(self, record: "Record") -> None:
        ConnectionManager(self).query_details(record)

    def get_modlist(self, record: "Record") -> None:
        ConnectionManager(self).query_modlist(record)

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

    def set_alerts(self, count: tuple[int]) -> None:
        self.alerts = count

    def get_alerts(self) -> tuple[int]:
        log_man = LogManager()
        alerts = log_man.get_alerts(self.prefs.paths.debug)
        return alerts
