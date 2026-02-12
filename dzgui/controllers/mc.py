import logging
import shutil
import threading
import traceback
from typing import Optional
from warnings import deprecated

from concurrent.futures import wait
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING

import dzgui.api.pefile as PeFile
import dzgui.api.servers as Servers
import dzgui.util._json as JSON  # noqa

from dzgui.api.probe import test_steam_api, test_bm_api
from dzgui.api.mods import (
    get_delimited_mods,
    get_local_mod_path,
    find_stale_mods,
    _hash,
    remove_stale_signatures,
)
from dzgui.const.enum import FilterMode, Preferences, NotebookPage, ButtonType, ContextMenu

from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    HEX_RED,
    WINDOW_DEFAULT_X,
    WINDOW_DEFAULT_Y,
)

from dzgui.config import update
from dzgui.config.query import lookup
from dzgui.config.userprefs import UserPrefs
from dzgui.controllers.emitter import Emitter
from dzgui.model.misc_model import ModelManager
from dzgui.util import strings
from dzgui.util.diag import write_diagnostic
from dzgui.util._json import read_json, write_json
from dzgui.util.localize import number
from dzgui.util.open_links import open_workshop_page, open_user_workshop
from dzgui.util.format import format_mods, format_player_count
from dzgui.util.redact import redact_log
from dzgui.views.dialogs.generic import ExceptionDialog, WaitDialog
from dzgui.views.dialogs.filepicker import FilePicker

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject  # noqa E402

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dzgui.const.enum import ServerTab
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


class Controller(GObject.GObject):
    def __init__(self) -> None:
        self.dist_cache: dict[str, "Haversine", "ServerTab"] = {}
        self.mediator = AppNavigation()
        self.prefs: UserPrefs

        self.model_man = ModelManager()
        self.emitter = Emitter()

        # NOTE: suppress requests until entire UI is loaded
        self.loaded = False


    def get_emitter(self) -> Emitter:
        return self.emitter

    def call_on_thread(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            self = args[0]
            self.wait_dialog = WaitDialog(self, strings.dialog.filtering)
            self.wait_dialog.show_all()
            thread = threading.Thread(target=func, args=args)
            thread.start()
        return wrapper

    def register_widget(self, attr: str, widget: Gtk.Widget) -> None:
        try:
            setattr(self.mediator, attr, widget)
        except AttributeError:
            logger.critical(f"{attr} is not a valid AppNavigation attribute.")

    def get_help_store(self) -> Gtk.ListStore:
        return self.model_man.get_help_store()

    def get_map_store(self) -> Gtk.ListStore:
        return self.model_man.get_map_store()

    def get_modlist_store(self) -> Gtk.ListStore:
        return self.model_man.get_modlist_store()

    def get_mod_store(self) -> Gtk.ListStore:
        return self.model_man.get_mod_store()

    def get_log_store(self) -> Gtk.ListStore:
        return self.model_man.get_log_store()

    def terminate_process(self) -> None:
        # TODO: only used by server table multiprocessing queue
        self.get_active_treeview().terminate_process()

    def get_prefs(self) -> UserPrefs:
        return self.prefs

    def set_prefs(self, prefs: UserPrefs) -> None:
        self.prefs = prefs

    def query_config(self, key: Preferences) -> str | bool | list:
        config = self.prefs.paths.config
        return lookup(config, key)

    def is_auto_install(self) -> bool:
        return self.query_config(Preferences.INSTALL)

    def reinit_map_store(self) -> None:
        self.model_man.set_all_maps()

    def append_map(self, map_row: list) -> None:
        self.model_man.append_map(map_row)

    def unblock_signals(self) -> None:
        self.block_signals(False)

    def block_signals(self, state: bool = True) -> None:
        self.suppress_signal(
            self.mediator.filters,
            self.mediator.filters.maps_combo,
            "_on_map_changed",
            state,
        )
        self.suppress_signal(
            self.mediator.menu,
            self.mediator.menu.selected_row,
            "_on_tree_selection_changed",
            state,
        )
        self.suppress_signal(
            self.mediator.menu, self.mediator.menu, "_on_keypress", state
        )
        for check in self.mediator.filters.checks:
            self.suppress_signal(
                self.mediator.filters,
                check,
                "_on_check_toggled",
                state,
            )

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

    def get_active_context(self) -> NotebookPage:
        tv = self.get_active_treeview()
        return tv.get_enum()

    def get_active_treeview(self) -> "ServerTreeView":
        return self.mediator.notebook.servers.get_active_treeview()

    def grab_active_treeview(self) -> None:
        self.get_active_treeview().grab_focus()

    def save_res_and_quit(self, *args: Any) -> None:
        treeview = self.get_active_treeview()
        columns = treeview.get_columns()

        columns_file = self.prefs.paths.columns
        try:
            data = JSON.read_json(columns_file)
        except Exception as e:
            logger.critical(e)
            data = {"cols": {}}

        for column in columns:
            title = column.get_title()
            size = column.get_width()
            data["cols"][title] = size

        try:
            JSON.write_json(data, columns_file)
        except Exception as e:
            logger.critical(e)

        logger.info("Normal user exit")
        if self.mediator.window.props.is_maximized:
            Gtk.main_quit()
            return

        w, h = self.mediator.window.get_size()
        data = {"res": {"width": w, "height": h}}

        res_path = self.prefs.paths.resolution
        try:
            write_json(data, res_path)
        except Exception as e:
            logger.critical(e)

        Gtk.main_quit()

    @deprecated("use statusbar internal contexts")
    def remove_statusbar(self, context: str) -> None:
        c = self.mediator.statusbar.statusbar.get_context_id(context)
        self.mediator.statusbar.statusbar.pop(c)

    @deprecated("use set_by_context")
    def set_statusbar(self, text: str, context: str) -> int:
        msg_id = self.mediator.statusbar.set_text(text, context)
        return msg_id

    def set_statusbar_dist(self, haversine: "Haversine", enum: "ServerTab") -> None:
        context = self.get_active_context()
        page = self.mediator.notebook.get_page_by_enum()
        """
        NOTE: prevents race condition when server tab changed,
        but allows caching the distance in the background
        """
        if page != NotebookPage.SERVERS:
            self.emitter.emit("distcalc_ended" , None, context)
            return
        if enum != context:
            self.emitter.emit("distcalc_ended" , None, context)
            return

        # NOTE: user may have changed km/mi toggle, so recalculate
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

    def load_mods(self) -> None:
        # TODO: threading
        model = self.model_man.get_mod_store()
        model.clear()
        path = self.query_config(Preferences.DEFAULT)
        mods = get_delimited_mods(Path(path))

        for mod in mods:
            # NOTE: holds color column
            mod.append(None)
            model.append(mod)

    def toggle_config(self, context: Preferences) -> None:
        config = self.prefs.paths.config
        try:
            update.toggle_config(config, context)
            # NOTE: 'use_miles' key is updated dynamically for statusbar unit
            if context == Preferences.DIST:
                self.prefs.use_miles = not self.prefs.use_miles
        except Exception as e:
            logger.critical(e)
            trace = traceback.format_exc()
            dialog = ExceptionDialog(self, trace)
            dialog.run()

    def update_config(self, key: Preferences, value: str) -> None:
        try:
            update.write_config(self.prefs.paths.config, key, value)
        except Exception as e:
            logger.critical(e)
            trace = traceback.format_exc()
            dialog = ExceptionDialog(self, trace)
            dialog.run()
            # TODO: suppress signals
            # then reenable (or it spawns dialog twice)
            self.mediator.grid.notebook.settings.populate_settings()
            return

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
        #self.mediator.notebook.set_page_by_enum(button.opens)

    def dump_api(self) -> None:
        self.first_iteration = True
        key = self.query_config(Preferences.STEAM)
        job = Servers.query_api
        params = Servers.params
        serv = []
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(job, key, APPID_DAYZ, param)
                for param in params
            ]
            wait(futures)
            for future in futures:
                res = future.result()
                if res.status != 200 or not res.parsed:
                    # TODO: pop warning dialog, create enum around various failure states
                    print("failed to parse/timeout error")
                    self.new_maps = None
                    self.push_data(None, FilterMode.INITIAL, success=False)
                    return
                j = res.json
                serv += j["response"]["servers"]

        res = Servers.query_api(key, APPID_DAYZ_EXP, "")
        if res.status == 200 and res.parsed is True:
            j = res.json
            serv += j["response"]["servers"]

        # TODO: additional ping column pass, collated
        parsed = Servers.parse_json(serv)
        self.new_maps = parsed
        self.push_data(parsed, FilterMode.INITIAL, success=True)

    def get_help_row(self) -> str:
        tv = self.mediator.menu
        model = self.get_help_store()
        tree_iter = tv.get_focused_row_iter()
        value = model.get_value(tree_iter, 1)
        return value.dict["tooltip"]

    def open_user_workshop(self, uid: str) -> None:
        # NOTE: uid may contain leading zeroes, not a real integer
        client = self.query_config(Preferences.CLIENT)
        open_user_workshop(uid, client)

    def copy_log(self, paths: list[Gtk.TreePath]) -> str:
        if len(paths) < 1:
            return ""
        final = []
        for path in paths:
            record = self.log_store[path]
            r = [el for el in record]
            concat = strings.delimiter.join(r)
            final.append(concat)
        text = "\n".join(final)
        return text

    def get_col_value_by_path_index(self, path: Gtk.TreePath, index: int) -> Any:
        treeview = self.get_active_treeview()
        model = treeview.get_model()
        if model is None:
            return None
        value = model[path][index]
        return value

    def copy_name(self, path: Gtk.TreePath) -> None:
        # TODO: column values are deterministic, perhaps use a col name to index map
        name = self.get_col_value_by_path_index(path, 0)
        if name is None:
            return
        self.copy_clipboard(name)

    def copy_ip(self, path: Gtk.TreePath) -> None:
        treeview = self.get_active_treeview()
        record = treeview.get_record()
        self.copy_clipboard(f"{record.ip}:{record.qport}")

    def copy_clipboard(self, text: str) -> None:
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.clipboard.set_text(text, -1)

    def open_mod_page(self, path: Gtk.TreePath) -> None:
        mod, it = self.model_man.get_mod_from_tree_path(path)
        cmd = self.query_config(Preferences.CLIENT)
        open_workshop_page(mod, cmd)

    # TODO: put in model manager (dedicated manager for mod store)
    #def get_mod_from_tree_path(
    #    self, tree_path: Gtk.TreePath
    #) -> tuple[str, Gtk.TreeIter]:
    #    model = self.model_man.get_mod_store()
    #    tree_iter = model.get_iter(tree_path)
    #    mod = model.get(tree_iter, 2)[0]
    #    return mod, tree_iter

    def delete_single_mod(self, tree_path: Gtk.TreePath) -> None:
        config = self.prefs.paths.config
        mod, it = self.model_man.get_mod_from_tree_path(tree_path)

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

        model = self.model_man.get_mod_store()
        model.remove(it)

    def format_mod_statusbar(self) -> None:
        total_mods, total_size = self.calc_mod_size()
        msg = format_mods(total_size, total_mods)
        return msg

    def calc_mod_size(self) -> tuple[int, int]:
        model = self.model_man.get_mod_store()
        total_mods = len(model)
        total_size = 0
        for mod in model:
            total_size += mod[3]
        return total_mods, total_size

    def menu_action(self, action: ContextMenu, path: Gtk.TreePath) -> None:
        match action:
            # NOTE: manipulates server stores
            # TODO: unimplemented
            case ContextMenu.ADD_SERVER:
                pass
            case ContextMenu.ADD_NOTE:
                pass
            case ContextMenu.COPY_CLIPBOARD:
                self.copy_ip(path)
            case ContextMenu.COPY_NAME:
                self.copy_name(path)
            case ContextMenu.REFRESH_PLAYERS:
                pass
            case ContextMenu.REMOVE_HISTORY:
                pass
            case ContextMenu.REMOVE_SERVER:
                pass
            case ContextMenu.SET_FAV:
                treeview = self.get_active_treeview()
                name = treeview.get_value_at_index(0)
                record = treeview.get_record_string()

                self.update_config(Preferences.FAV_LBL, name)
                self.update_config(Preferences.FAV_SRV, record)
                # TODO: consider a failure dialog here

                simple_ip = treeview.get_simplified_ip()
                self.emitter.emit("fav_server_changed", name, simple_ip)
            case ContextMenu.SHOW_DETAILS:
                pass
            case ContextMenu.SHOW_MODS:
                pass

            # NOTE: manipulates mod store
            case ContextMenu.DELETE_MOD:
                self.delete_single_mod(path)
                # TODO: connect to emitter automatically
                # Gtk.TreeModel, row-inserted/row-deleted
                # updates statusbar
                self.update_mod_statusbar()
                remove_stale_signatures(
                    self.prefs.paths.config, self.prefs.paths.version
                )

            case ContextMenu.OPEN_WORKSHOP:
                self.open_mod_page(path)

    def toggle_mod_selection(self, state: bool) -> None:
        sel = self.mediator.modtreeview.get_selection()
        if state:
            sel.select_all()
        else:
            sel.unselect_all()
        self.mediator.modtreeview.grab_focus()

    def populate_log(self) -> None:
        log = self.prefs.paths.debug
        store = self.model_man.get_log_store()
        store.clear()
        # NOTE: this model is reloaded each time as log changes
        try:
            with open(log, "r") as f:
                lines = [
                    line.split(strings.delimiter) for line in f.read().splitlines()
                ]
                for record in lines:
                    clean = redact_log(record)
                    store.append(clean)
        except Exception as e:
            dialog = ExceptionDialog(self, str(e))
            dialog.run()
            return
        self.open_page(NotebookPage.LOG)

    def select_colorized(self) -> None:
        model = self.model_man.get_mod_store()
        sel = self.mediator.modtreeview.get_selection()
        for mod in model:
            it = mod.iter
            path = model.get_path(it)
            if mod[4] == HEX_RED:
                sel.select_path(path)

    def uncolorize_mods(self) -> None:
        model = self.model_man.get_mod_store()
        for mod in model:
            it = mod.iter
            path = model.get_path(it)
            model[path][4] = None

    def colorize_mods(self) -> None:
        model = self.model_man.get_mod_store()
        stale = find_stale_mods(self.prefs.paths.config)
        for mod in model:
            it = mod.iter
            path = model.get_path(it)
            # TODO: consider storing in ListStore as int
            if int(mod[2]) in stale:
                model[path][4] = HEX_RED

        self.destroy_on_idle()

    def unselect_all_mods(self) -> None:
        self.mediator.modtreeview.get_selection().unselect_all()

    def dump_test_2(self) -> None:
        import time
        time.sleep(1)
        data = (
            ["BAR", "a", "a", "a", 1, 1, 1, "185.207.214.16:2302", 1, 1, "a", False],
            ["BAR", "a", "a", "a", 1, 1, 1, "172.111.51.156:2302", 1, 1, "a", False],
            ["BAR", "a", "a", "a", 1, 1, 1, "185.207.214.16:2302", 1, 1, "a", False],
            ["BAR", "a", "a", "a", 1, 1, 1, "185.207.214.16:2302", 1, 1, "a", False],
            ["BAR", "a", "a", "a", 1, 1, 1, "185.207.214.16:2302", 0, 0, "a", False],
            ["BAR", "a", "a", "a", 1, 1, 1, "185.207.214.16:2302", 0, 0, "a", False],
            ["BAR", "a", "a", "a", 1, 1, 1, "185.207.214.16:2302", 0, 0, "a", False],
            ["BAR", "a", "a", "a", 1, 1, 1, "185.207.214.16:2302", 0, 0, "a", False],
            ["BAR", "a", "a", "a", 1, 1, 1, "185.207.214.16:2302", 0, 0, "a", False],
            ["BAR", "a", "a", "a", 1, 1, 1, "185.207.214.16:2302", 0, 0, "a", False],
            ["BAR", "a", "a", "a", 1, 1, 1, "185.207.214.16:2302", 0, 0, "a", False],
        )
        self.push_data(data, FilterMode.INITIAL, success=True)

    # TODO: eg cleanup on failure, cleanup on sucess
    # separate methods
    def cleanup(self) -> None:
        treeview = self.get_active_treeview()

        # TODO: signals or other approach to deferring map
        # model insertion after thread closes
        # cf. servers_loaded signal
        treeview.set_model(self.to_insert)

        # CHORE: this is placeholder logic
        if self.first_iteration:
            self.mediator.filters.set_unique_maps(self.new_maps)
            self.first_iteration = False

        context = self.get_active_context()
        self.emitter.emit("servers_loaded", context)

        treeview.grab_focus()
        self.destroy_on_idle()
        if self.success is False:
            # TODO: different dialogs for server tab contexts, e.g. lan timeout
            # TODO: if history/favorites is empty, don't even trigger a call to dump data
            dialog = ExceptionDialog(self, "API TIMEOUT")
            dialog.run()

    def push_data(self, data: tuple, mode: Optional[FilterMode], success: bool) -> None:

        treeview = self.get_active_treeview()
        manager = treeview.get_filter_man()

        self.to_insert = None

        # TODO:
        self.success = success
        if success:
            if data is None:
                self.to_insert = None
            else:
                # TODO: consolidate into filter manager
                if mode == FilterMode.INITIAL:
                    manager.set_control(data)
                manager.filter(mode)
                self.to_insert = manager.get_model()
            # TODO: should list store be set outside of this thread?
            # treeview.set_model(self.to_insert)
        treeview.set_loaded(True)
        GLib.idle_add(self.cleanup)

    @call_on_thread
    def highlight_stale(self) -> None:
        self.colorize_mods()

    def get_callback(self) -> Callable | None:
        return self.callback["func"]

    def get_callback_args(self) -> Any:
        return self.callback["args"]

    def set_callback(self, callback: Callable | None, *args) -> None:
        """
        Lets calling widgets register a callback function
        when spawning a threaded process
        """
        self.callback = {"func": callback, "args": args}

    def destroy_on_idle(self) -> None:
        self.wait_dialog.destroy()
        func = self.get_callback()
        self.mediator.window.set_sensitive(True)
        # TODO: spawn error dialog if API crawl failed
        if func is not None:
            args = self.get_callback_args()
            GLib.idle_add(func, *args)
            self.set_callback(None, None)

    def dump_diagnostics(self) -> None:
        picker = FilePicker(self.mediator.window)
        file = picker.pick_file()
        if file is not None:
            try:
                write_diagnostic(self.prefs.paths.config, file)
            except Exception as e:
                dialog = ExceptionDialog(self, str(e))
                dialog.run()

    def test_api_response(self, text: str, key: Preferences) -> None:
        if key is Preferences.STEAM:
            res = test_steam_api(text)
        else:
            res = test_bm_api(text)

        if res is True:
            self.update_config(key, text)
            self.set_callback(None, None)
            self.destroy_on_idle()
        else:
            self.destroy_on_idle()
            dialog = ExceptionDialog(self, strings.api_error)
            dialog.run()

    @call_on_thread
    # FIXME: entire process is behind thread, including destroy_on_idle()
    def update_api_key(self, text: str, key: Preferences) -> None:
        self.test_api_response(text, key)

    def set_resolution(self, window: "OuterWindow") -> None:
        if self.prefs.is_game_mode:
            window.fullscreen()
            return
        elif self.query_config(Preferences.WINDOW) is True:
            window.fullscreen()

        try:
            data = read_json(self.prefs.paths.resolution)
            valid_json = True
        except Exception as e:
            valid_json = False
            logger.critical(e)

        if valid_json:
            res = data["res"]
            w, h = res["width"], res["height"]
            logger.info(f"Restoring window size to {w},{h}")
            window.set_default_size(w, h)
        else:
            w = WINDOW_DEFAULT_X
            h = WINDOW_DEFAULT_Y
            logger.info(f"Using default window size {w},{h}")
            window.set_default_size(w, h)

    def propagate_column_width(self, col: Gtk.TreeViewColumn) -> None:
        GLib.idle_add(self.mediator.servers.update_tab_widths, col)

    def refresh_tree(self) -> None:
        treeview = self.get_active_treeview()
        treeview.set_loaded(False)
        self.populate_model()

    def get_player_count(self) -> str:
        treeview = self.get_active_treeview()
        model = treeview.get_model()
        control_model = treeview.filter_man.get_control()
        count = format_player_count(model, control_model)
        return count

    def get_statusbar(self) -> None:
        return self.mediator.statusbar

    @call_on_thread
    def run_query_func(self, func: Callable) -> None:
        func()

    @call_on_thread
    def filter_threaded(self, mode: FilterMode, label: str) -> None:
        tv = self.get_active_treeview()
        tv.filter_man.filter(mode, label)
        self.push_data("", mode, success=True)

    # FIXME: optional label/map/keyword parameter
    def refilter_model(self, mode: FilterMode, label: Optional[str] = None) -> None:
        tv = self.get_active_treeview()
        if tv.filter_man.get_control() is None:
            return
        tv.set_model(None)
        # TODO: deprecated in this context?
        self.set_callback(None, None)
        self.filter_threaded(mode, label)

    def populate_model(self) -> None:
        treeview = self.get_active_treeview()
        if treeview.is_loaded() is True:
            self.emitter.emit("servers_loaded", treeview.get_enum())
            return

        treeview.set_model(None)
        func = treeview.get_query_func()
        if func is None:
            self.emitter.emit("servers_loaded", treeview.get_enum())
            return
        # TODO:
        # manager = treeview.get_filter_man()
        # manager.clear_model()
        self.set_callback(None, None)
        self.run_query_func(func)

    def get_favorite(self) -> tuple[str, str] | tuple[None, None]:
        fav = str(self.query_config(Preferences.FAV_LBL))
        if len(fav) < 1:
            return None, None
        ip = str(self.query_config(Preferences.FAV_SRV))
        addr = ip.split(":")
        return fav, f"{addr[0]}:{addr[2]}"

    def get_dist_cache(self) -> dict[str, "Haversine"]:
        return self.dist_cache

    # TODO: use model manager, map and keyword caches
    # TODO: model cache that hooks checkbox signal
    def get_filters(self) -> list:
        return self.mediator.filters.get_filters()

    def get_keyword(self) -> str:
        return self.mediator.filters.get_keyword_filter()

    def get_map(self) -> str:
        return self.mediator.filters.get_selected_map()

    def get_prior_map(self) -> str:
        return self.mediator.filters.get_prior_map()
