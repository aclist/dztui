import logging
import shutil
import threading
import textwrap
import traceback

from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING

import dzgui.api.pefile as PeFile
import dzgui.util._json as JSON  # noqa
from dzgui.views.dialogs.generic import ExceptionDialog

from dzgui.api.probe import test_steam_api, test_bm_api
from dzgui.api.mods import (
    get_delimited_mods,
    get_local_mod_path,
    find_stale_mods,
    _hash,
    remove_stale_signatures
)
from dzgui.const.enum import (
    Preferences,
    Popup,
    NotebookPage,
    ButtonType,
    ContextMenu,
    RowType
)

from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    HEX_RED,
    WINDOW_DEFAULT_X,
    WINDOW_DEFAULT_Y
)

from dzgui.config import update
from dzgui.config.query import lookup
from dzgui.config.userprefs import UserPrefs
from dzgui.controllers.model import ModelManager
from dzgui.util import strings
from dzgui.util.diag import write_diagnostic
from dzgui.util._json import read_json, write_json
from dzgui.util.localize import number
from dzgui.util.open_links import open_workshop_page, open_user_workshop
from dzgui.util.format import format_mods, format_player_count, pluralize
from dzgui.util.redact import redact_log

from dzgui.views.dialogs.filepicker import FilePicker
from dzgui.views.dialogs.generic import GenericDialog

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject # noqa E402

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dzgui.util.dist import Haversine
    from dzgui.views.base import Notebook, Grid, OuterWindow
    from dzgui.views.components.buttonbox import ContextualButton
    from dzgui.views.components.statusbar import Statusbar
    from dzgui.views.components.right_panel import RightPanel
    from dzgui.views.pages.servers import ServerNotebook
    from dzgui.views.trees.tree_base import TreeView
    from dzgui.views.trees.tree_menu import MenuTreeView
    from dzgui.views.trees.tree_mods import ModTreeView
    from dzgui.views.trees.tree_servers import ServerTreeView
    from dzgui.views.trees.tree_log import LogTreeView

class AppNavigation:
    window: "OuterWindow"
    grid: "Grid"
    right_panel: "RightPanel"
    statusbar: "Statusbar"
    notebook: "Notebook"
    modtreeview: "ModTreeView"
    menu: "MenuTreeView"
    servers: "ServerNotebook"
    browser: "ServerTreeView"
    saved: "ServerTreeView"
    recent: "ServerTreeView"
    lan: "ServerTreeView"
    logtreeview: "LogTreeView"

class Controller:
    def __init__(self) -> None:
        self.dist_cache: dict[str, "Haversine"] = {}
        self.crumbs_cache = ""
        self.mediator = AppNavigation()
        self.prefs: UserPrefs

        self.model_manager = ModelManager()

    def register_widget(self, attr: str, widget: Gtk.Widget) -> None:
        try:
            setattr(self.mediator, attr, widget)
        except AttributeError:
            logger.critical(f"{attr} is not a valid AppNavigation attribute.")

    def set_crumbs(self, text: str) -> None:
        self.mediator.grid.set_breadcrumbs(text)

    def get_crumbs(self) -> str:
        return self.mediator.grid.get_breadcrumbs()

    def get_server_store(self) -> Gtk.ListStore:
        return self.model_manager.get_server_store()

    def get_saved_store(self) -> Gtk.ListStore:
        return self.model_manager.get_saved_store()

    def get_recent_store(self) -> Gtk.ListStore:
        return self.model_manager.get_recent_store()

    def get_lan_store(self) -> Gtk.ListStore:
        return self.model_manager.get_lan_store()

    def get_help_store(self) -> Gtk.ListStore:
        return self.model_manager.get_help_store()

    def get_map_store(self) -> Gtk.ListStore:
        return self.model_manager.get_map_store()

    def get_modlist_store(self) -> Gtk.ListStore:
        return self.model_manager.get_modlist_store()

    def get_mod_store(self) -> Gtk.ListStore:
        return self.model_manager.get_mod_store()

    def get_log_store(self) -> Gtk.ListStore:
        return self.model_manager.get_log_store()

    def terminate_process(self) -> None:
        # TODO: only used by server table multiprocessing queue
        self.mediator.notebook.servers.browser.terminate_process()

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
        self.model_manager.set_all_maps()

    def append_map(self, map_row: list) -> None:
        self.model_manager.append_map(map_row)

    def unblock_signals(self) -> None:
        self.block_signals(False)

    def block_signals(self, state: bool = True) -> None:
        self.suppress_signal(
            self.mediator.grid.right_panel.filters_vbox,
            self.mediator.grid.right_panel.filters_vbox.maps_combo,
            "_on_map_changed",
            state,
        )
        self.suppress_signal(
            self.mediator.menu,
            self.mediator.menu.selected_row,
            "_on_tree_selection_changed",
            state,
        )
        self.suppress_signal(self.mediator.menu, self.mediator.menu, "_on_keypress", state)
        for check in self.mediator.grid.right_panel.filters_vbox.checks:
            self.suppress_signal(
                self.mediator.grid.right_panel.filters_vbox,
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
        # TODO: deprecated?
        #self.mediator.menu.sel_blocked = state

    def toggle_debug_mode(self) -> None:
        self.toggle_config(Preferences.DEBUG)

    def get_active_treeview(self) -> "TreeView":
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

    def get_statusbar(self) -> str:
        return self.mediator.statusbar.get_text()

    def set_statusbar(self, text: str) -> None:
        self.mediator.statusbar.set_text(text)

    def set_statusbar_placeholder(self, text: str) -> None:
        self.statusbar_placeholder = text

    def set_statusbar_dist(self, haversine: "Haversine") -> None:
        dist: str
        if haversine is None:
            dist = "Unknown"
        else:
            if self.query_config(Preferences.DIST) is True:
                raw = round(haversine.as_miles())
                separated = number(raw)
                dist = str(separated) + " mi"
            else:
                raw = round(haversine.as_kilometers())
                separated = number(raw)
                dist = str(separated) + " km"
        text = self.statusbar_placeholder
        self.set_statusbar(f"{text} | Distance: {dist}")

    def delete_multiple_mods(self) -> None:
        sel = self.mediator.modtreeview.get_selection()
        model, pathlist = sel.get_selected_rows()
        # NOTE: reverse when multiple selection
        for path in reversed(pathlist):
            self.delete_single_mod(path)

        total_mods, total_size = self.calc_mod_size()
        self.update_mod_statusbar()

    def load_mods(self) -> None:
        model = self.model_manager.get_mod_store()
        model.clear()
        path = self.query_config(Preferences.DEFAULT)
        mods = get_delimited_mods(Path(path))

        for mod in mods:
            # NOTE: holds color column
            mod.append(None)
            model.append(mod)

        self.update_mod_statusbar()

    def toggle_config(self, context: Preferences) -> None:
        config = self.prefs.paths.config
        try:
            update.toggle_config(config, context)
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

    # NOTE: disabled for now
    #def present_toast(self, text: str) -> None:
    #    self.mediator.window.toast.set_text_and_fade(text)

    def open_keybindings(self) -> None:
        notebook = self.mediator.grid.notebook
        notebook.toggle_keybindings()

    def focus_notebook(self) -> None:
        notebook = self.mediator.grid.notebook
        notebook.focus_current()

    # TODO: deprecated
    def spawn_dialog(self, msg: str, mode: Popup) -> bool:
        """
        Spawns a GenericDialog transient to the OuterWindow
        """
        msg = textwrap.dedent(msg)
        dialog = GenericDialog(self, msg, mode)
        response = dialog.run()
        dialog.destroy()

        match response:
            case Gtk.ResponseType.OK:
                return False
            case Gtk.ResponseType.CANCEL | Gtk.ResponseType.DELETE_EVENT:
                return True
        return False

    def set_statusbar_by_row(self, row: "RowType") -> None:
        self.mediator.statusbar.refresh(row)

    def toggle_server_panels(self, state: bool) -> None:
        self.mediator.grid.toggle_filter_panel(state)
        self.mediator.grid.toggle_connect_panel(state)
        self.mediator.grid.toggle_refresh_button(state)

    def toggle_mod_panel(self, state: bool) -> None:
        self.mediator.grid.right_panel.sel_panel.set_visible(state)

    def show_developers_page(self) -> None:
        self.open_page(NotebookPage.DEVELOPERS)
        # TODO: put cursor on first row
        #self.mediator.developers.focus_first_row()

    def open_page(self, page: NotebookPage) -> None:
        self.mediator.grid.notebook.set_page_by_enum(page)

    def open_page_by_button(self, button: "ContextualButton") -> None:
        # TODO: consolidate methods with set_page_by_enum
        match button.context:
            case ButtonType.EXIT:
                logger.info("Normal user exit")
                self.save_res_and_quit()
                return
            case ButtonType.OPTIONS:
                self.mediator.grid.notebook.settings.populate_settings()
            case ButtonType.MODS:
                self.load_mods()
            case ButtonType.HELP:
                self.mediator.statusbar.refresh(RowType.CHANGELOG)
                pass
            case ButtonType.SERVERS:
                self.mediator.notebook.set_page_by_enum(button.opens)
                # TODO: use cache
                self.update_server_status()
                return

        self.mediator.notebook.set_page_by_enum(button.opens)
        self.set_crumbs(button.get_label())

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

    def copy_clipboard(self, text: str) -> None:
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.clipboard.set_text(text, -1)

    def open_mod_page(self, path: Gtk.TreePath) -> None:
        mod, it = self.get_mod_from_tree_path(path)
        cmd = self.query_config(Preferences.CLIENT)
        open_workshop_page(mod, cmd)

    # TODO: put in model manager (dedicated manager for mod store)
    def get_mod_from_tree_path(self, tree_path: Gtk.TreePath) -> tuple[str, Gtk.TreeIter]:
        model = self.model_manager.get_mod_store()
        tree_iter = model.get_iter(tree_path)
        mod = model.get(tree_iter, 2)[0]
        return mod, tree_iter

    def delete_single_mod(self, tree_path: Gtk.TreePath) -> None:
        config = self.prefs.paths.config

        mod, it = self.get_mod_from_tree_path(tree_path)

        path = lookup(config, Preferences.DEFAULT)
        steam_path = Path(path)
        mods_path = get_local_mod_path(steam_path)
        app_path = PeFile.get_nested_app_path(steam_path, APPID_DAYZ)

        md5 = _hash(mod)
        symlink =  app_path / md5
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

        model = self.model_manager.get_mod_store()
        model.remove(it)


    def update_mod_statusbar(self) -> None:
        total_mods, total_size = self.calc_mod_size()
        msg = format_mods(total_size, total_mods)
        self.mediator.statusbar.set_text(msg)

    def calc_mod_size(self) -> tuple[int, int]:
        model = self.model_manager.get_mod_store()
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
            case ContextMenu.ADD_FAV:
                pass
            case ContextMenu.ADD_NOTE:
                pass
            case ContextMenu.COPY_CLIPBOARD:
                pass
            case ContextMenu.COPY_NAME:
                pass
            case ContextMenu.REFRESH_PLAYERS:
                pass
            case ContextMenu.REMOVE_HISTORY:
                pass
            case ContextMenu.REMOVE_SERVER:
                pass
            case ContextMenu.SHOW_DETAILS:
                pass
            case ContextMenu.SHOW_MODS:
                pass

            # NOTE: manipulates mod store
            case ContextMenu.DELETE_MOD:
                self.delete_single_mod(path)
                self.update_mod_statusbar()
                remove_stale_signatures(
                    self.prefs.paths.config,
                    self.prefs.paths.version
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
        store = self.model_manager.get_log_store()
        store.clear()

        # TODO: pop dialog if log is missing
        with open(log, "r") as f:
            lines = [line.split(strings.delimiter) for line in f.read().splitlines()]
            for record in lines:
                clean = redact_log(record)
                store.append(clean)
        self.open_page(NotebookPage.LOG)

    def select_colorized(self) -> None:
        model = self.model_manager.get_mod_store()
        sel = self.mediator.modtreeview.get_selection()
        for mod in model:
            it = mod.iter
            path = model.get_path(it)
            if mod[4] == HEX_RED:
                sel.select_path(path)

    def uncolorize_mods(self) -> None:
        model = self.model_manager.get_mod_store()
        for mod in model:
            it = mod.iter
            path = model.get_path(it)
            model[path][4] = None

    def colorize_mods(self) -> None:
        model = self.model_manager.get_mod_store()
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

    def highlight_stale(self) -> None:
        self.call_on_thread(self.colorize_mods)

    def call_on_thread(self, func: Callable, *args) -> None:
        self.wait_dialog = GenericDialog(self, strings.dialog.fetching, Popup.WAIT)
        self.wait_dialog.show_all()
        thread = threading.Thread(target=func, args=args)
        thread.start()

    def destroy_on_idle(self) -> None:
        self.wait_dialog.destroy()
        # TODO: improve upon this
        func = self.callback["func"]
        if func is not None:
            args = self.callback["args"]
            GLib.idle_add(func, *args)
            self.set_callback(None, None)

    def set_callback(self, callback: Callable | None, *args) -> None:
        """
        Lets calling widgets register a callback function
        when spawning a threaded process
        """
        self.callback = { "func": callback, "args": args }

    def dump_diagnostics(self) -> None:
        picker = FilePicker(self.mediator.window)
        file = picker.pick_file()
        if file is not None:
            try:
                write_diagnostic(self.prefs.paths.config, file)
            except Exception as e:
                self.spawn_dialog(str(e), Popup.NOTIFY)

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
            self.spawn_dialog(strings.api_error, Popup.NOTIFY)


    def update_api_key(self, text: str, key: Preferences) -> None:
        self.call_on_thread(self.test_api_response, text, key)

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

    def update_server_status(self) -> None:
        treeview = self.mediator.notebook.servers.get_active_treeview()
        model = treeview.get_model()
        status = format_player_count(model)
        self.set_statusbar_placeholder(status)
        self.set_statusbar(status + "| Calculating...")

    def propagate_column_width(self, col: Gtk.TreeViewColumn) -> None:
        GLib.idle_add(self.mediator.servers.update_tab_widths, col)

    def set_crumbs_cache(self, text: str) -> None:
        self.crumbs_cache = text

    def get_crumbs_cache(self) -> str:
        return self.crumbs_cache

    def refresh_tree(self) -> None:
        treeview = self.mediator.notebook.servers.get_active_treeview()
        treeview.set_loaded(False)
        self.populate_model()

    def populate_model(self) -> None:
        # TODO: always use same server model, store in servertreeview class
        treeview = self.get_active_treeview()
        if treeview.get_loaded() is False:
            new_model = self.model_manager.new_model()
            # NOTE: set_query_func()
            func = treeview.get_query_func()
            if func is not None:
                model = treeview.get_model()
                model.clear()
                data = func()
                # TODO: threading
                model.append(data)
            treeview.set_loaded(True)
            self.update_server_status()
        treeview.grab_focus()

    def focus_button_box(self) -> None:
        self.mediator.right_panel.focus_button_box()

    def present_servers(self) -> None:
        # TODO: abstract
        self.grab_active_treeview()
        self.update_server_status()
        crumbs = self.mediator.servers.get_cached_label()
        self.set_crumbs(crumbs)
        # TODO: could emit this when treeview gains keyboard focus
        #tree = self.get_active_treeview()
        #tree.emit("on_distcalc_started")

    def toggle_check(self, event: Gdk.EventKey) -> None:
        keyname = Gdk.keyval_name(event.keyval)
        if keyname.isnumeric() and int(keyname) > 0:
            digit = int(keyname) - 1
            self.mediator.grid.right_panel.filters_vbox.toggle_check(digit)
        else:
            match event.keyval:
                case Gdk.KEY_0:
                    self.mediator.grid.right_panel.filters_vbox.toggle_check(9)
                case Gdk.KEY_minus:
                    self.mediator.grid.right_panel.filters_vbox.toggle_check(10)
                case Gdk.KEY_backslash:
                    self.mediator.grid.right_panel.filters_vbox.toggle_check(11)
                case _:
                    return False

    def get_favorite(self) -> tuple[str, str] | tuple[None, None]:
        fav = str(self.query_config(Preferences.FAV_LBL))
        if len(fav) < 1:
            return None, None
        ip = str(self.query_config(Preferences.FAV_SRV))
        addr = ip.split(":")
        return fav, f"{addr[0]}:{addr[2]}"

    def get_dist_cache(self) -> dict[str, "Haversine"]:
        return self.dist_cache

    def toggle_lan_panel(self, state: bool) -> None:
        self.mediator.grid.conpan.set_visible(state)
