import logging
import time

from pathlib import Path
from typing import TYPE_CHECKING

from dzgui.api.steam import unsubscribe
from dzgui.api.mods import (
    get_delimited_mods,
    find_stale_mods,
    _hash,
    remove_stale_signatures,
)
from dzgui.const.constants import (
    API_RATE_LIMIT,
    APP_NAME,
    APPID_DAYZ,
    APPID_DAYZ_EXP,
)
from dzgui.const.enum import Preferences
from dzgui.managers.threading import call_on_thread, StoredFunc, ThreadingManager
from dzgui.model.model_factory import FastInsertListStore, ModelFactory
from dzgui.strings import dialogs, kb
from dzgui.util.format import format_mods
from dzgui.util.strings import server_timeout
from dzgui.util.symlink import rebuild_symlinks
from dzgui.views.dialogs.generic import ExceptionDialog


import dzgui.api.pefile as PeFile

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

logger = logging.getLogger(APP_NAME)


class ModManager:
    """
    Because mods may be dynamically updated on the system,
    this manager is instantiated each time the Mods page is opened
    """

    def __init__(self, tree: Gtk.TreeView, controller: "Controller") -> None:
        self.treeview = tree
        self.controller = controller

        self.emitter = controller.get_emitter()
        self.prefs = controller.get_prefs()
        self.path = controller.query_config(Preferences.DEFAULT)

        self.store: FastInsertListStore | None = None

        self.thread_man = ThreadingManager(controller)

    @call_on_thread(dialogs.fetching_mods)
    def load_mods(self) -> None:
        mods = get_delimited_mods(Path(self.path))
        if len(mods) < 1:
            msg = self.format_mod_statusbar()
            func = StoredFunc(lambda: self.emitter.emit("mods_updated", msg, 0))
            self.thread_man.set_cleanup_func(func)
            return

        prefs = self.controller.get_prefs()
        rebuild_symlinks(prefs.paths.config)

        self.store = ModelFactory().make_mod_store()
        self.store.extend(mods)
        func = StoredFunc(self._on_mods_loaded)

        self.thread_man.set_cleanup_func(func)

    def set_store(self, store: "FastInsertListStore") -> None:
        self.store = store

    def _on_mods_loaded(self) -> None:
        self.treeview.set_model(self.store)
        if self.store is None:
            return
        msg = self.format_mod_statusbar()
        total_mods = len(self.store)
        self.emitter.emit("mods_updated", msg, total_mods)

    def unsub_mods(self) -> None:
        sel = self.treeview.get_selection()
        model, pathlist = sel.get_selected_rows()
        # NOTE: reverse when multiple selection
        mods: list[tuple[str, Gtk.TreeIter]] = []
        for path in reversed(pathlist):
            res = self.get_mod_from_tree_path(path)
            if res is None:
                continue
            mod, _iter = res
            mods.append((mod, _iter))
        self.thread_man.set_job_count(len(mods))
        self.unsub_all_mods(mods)

    def get_mod_from_tree_path(
        self, tree_path: Gtk.TreePath
    ) -> tuple[str, Gtk.TreeIter] | None:
        model = self.treeview.get_model()
        if model is None:
            return None
        tree_iter = model.get_iter(tree_path)
        mod = model.get_value(tree_iter, 2)
        return mod, tree_iter

    @call_on_thread(dialogs.deleting_mods)
    def unsub_all_mods(self, mods: list[tuple[str, Gtk.TreeIter]]) -> None:
        for mod, _iter in mods:
            self.unsub_atomic_mod(mod)
            self.thread_man.increment_dialog()
            time.sleep(API_RATE_LIMIT)

        func = StoredFunc(self._on_mods_unsubbed, mods)
        self.thread_man.set_cleanup_func(func)

    def unsub_atomic_mod(self, mod: str) -> None:
        config_man = self.controller.get_config_man()
        key = config_man.lookup(Preferences.STEAM)
        unsubscribe(key, int(mod))

        steam_path = Path(self.path)
        app_path = PeFile.get_nested_app_path(steam_path, APPID_DAYZ)

        try:
            md5 = _hash(mod)
            symlink = app_path / md5
            symlink.unlink()
        except Exception as e:
            logger.warning(e)
        # NOTE: second pass to unlink DAYZ_EXP mods
        # TODO: test this with working APPID_DAYZ_EXP installation
        try:
            app_path_exp = PeFile.get_nested_app_path(steam_path, APPID_DAYZ_EXP)
            symlink = app_path_exp / md5
            symlink.unlink()
        except Exception:
            pass
        time.sleep(API_RATE_LIMIT)

    def _on_mods_unsubbed(self, mod_iter: list[tuple[str, Gtk.TreeIter]]) -> None:
        mods = [int(mod) for mod, _iter in mod_iter]
        iters = [_iter for mod, _iter in mod_iter]
        if self.store is None:
            return
        for _iter in iters:
            self.store.remove(_iter)
        # TODO: process config path in called function
        remove_stale_signatures(self.prefs.paths.config, self.prefs.paths.version, mods)
        model = self.treeview.get_model()
        if model is None:
            return
        total_mods = len(model)
        msg = self.format_mod_statusbar()
        self.emitter.emit("mods_updated", msg, total_mods)

    def uncolorize_mods(self) -> None:
        model = self.treeview.get_model()
        if model is None:
            return
        for mod in model:
            _iter = mod.iter
            path = model.get_path(_iter)
            model[path][4] = None
        path = Gtk.TreePath.new_from_indices([0])
        self.treeview.set_cursor(path)

    def toggle_mod_selection(self, state: bool) -> None:
        sel = self.treeview.get_selection()
        if state:
            sel.select_all()
        else:
            sel.unselect_all()
        self.treeview.grab_focus()

    def format_mod_statusbar(self) -> str:
        total_mods, total_size = self.calc_mod_size()
        msg = format_mods(total_size, total_mods)
        return msg

    def calc_mod_size(self) -> tuple[int, int]:
        model = self.treeview.get_model()
        if model is None:
            return 0, 0
        total_mods = len(model)
        total_size = 0
        for mod in model:
            total_size += mod[3]
        return total_mods, total_size

    def _on_stale_mods_found(self, stale_mods: list) -> None:
        """Manipulates attached ListStore in the main event loop"""
        model = self.treeview.get_model()
        if model is None:
            return
        for mod in model:
            it = mod.iter
            path = model.get_path(it)
            if int(mod[2]) in stale_mods:
                model[path][4] = True
        self.emitter.emit("mods_highlighted")

    @call_on_thread(dialogs.scanning_mods)
    def highlight_stale(self) -> None:
        stale = find_stale_mods(self.prefs.paths.config)
        func = StoredFunc(self._on_stale_mods_found, stale)
        self.thread_man.set_cleanup_func(func)

    def _server_timeout(self) -> None:
        dialog = ExceptionDialog(self.controller, server_timeout)
        dialog.set_secondary_text(kb.DZG_006)
        dialog.run()

    def select_colorized(self) -> None:
        model = self.treeview.get_model()
        if model is None:
            return
        sel = self.treeview.get_selection()
        for mod in model:
            it = mod.iter
            path = model.get_path(it)
            if mod[4] is True:
                sel.select_path(path)
