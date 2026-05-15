import logging
import shutil

from pathlib import Path
from typing import Any, TYPE_CHECKING

from dzgui.api.mods import (
    get_delimited_mods,
    get_local_mod_path,
    find_stale_mods,
    _hash,
    remove_stale_signatures,
)
from dzgui.const.constants import APP_NAME, APPID_DAYZ, APPID_DAYZ_EXP
from dzgui.const.enum import Preferences
from dzgui.managers.threading import call_on_thread, StoredFunc, ThreadingManager
from dzgui.model.model_factory import FastInsertListStore, ModelFactory
from dzgui.util.format import format_mods
from dzgui.util.strings import server_timeout
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

    def __init__(self, controller: "Controller") -> None:
        self.controller = controller
        self.emitter = controller.get_emitter()
        self.prefs = controller.get_prefs()
        self.path = controller.query_config(Preferences.DEFAULT)
        self.treeview = self.controller.get_modtreeview()

        self.store: FastInsertListStore

        self.thread_man = ThreadingManager(controller)
        self._get_mods()

    # TODO: dialog strings
    @call_on_thread("getting mods")
    def _get_mods(self) -> None:
        mods = get_delimited_mods(self.path)
        if len(mods) < 1:
            msg = self.format_mod_statusbar()
            func = StoredFunc(lambda: self.emitter.emit("mods_updated", msg, 0))
            self.thread_man.set_cleanup_func(func)
            return

        func = StoredFunc(self._on_mods_loaded, mods)
        self.thread_man.set_cleanup_func(func)

    def _on_mods_loaded(self, mods: list[list[Any]]) -> None:
        self.store = ModelFactory().make_mod_store()
        self.store.extend(mods)
        self.treeview.set_model(self.store)
        msg = self.format_mod_statusbar()
        total_mods = len(self.store)
        self.emitter.emit("mods_updated", msg, total_mods)

    def delete_mods(self) -> None:
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
        self.delete_mods_on_system(mods)

    def get_mod_from_tree_path(
        self, tree_path: Gtk.TreePath
    ) -> tuple[str, Gtk.TreeIter] | None:
        model = self.treeview.get_model()
        if model is None:
            return None
        tree_iter = model.get_iter(tree_path)
        mod = model.get_value(tree_iter, 2)
        return mod, tree_iter

    # TODO: strings
    @call_on_thread("deleting mods")
    def delete_mods_on_system(self, mods: list[tuple[str, Gtk.TreeIter]]) -> None:
        for mod, _iter in mods:
            self.delete_single_mod(mod)

        iters = [_iter for mod, _iter in mods]
        func = StoredFunc(self._on_mods_deleted, iters)
        self.thread_man.set_cleanup_func(func)

    def delete_single_mod(self, mod: str) -> None:
        steam_path = Path(self.path)
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

    def _on_mods_deleted(self, iters: list[Gtk.TreeIter]) -> None:
        for _iter in iters:
            self.store.remove(_iter)
        remove_stale_signatures(self.prefs.paths.config, self.prefs.paths.version)
        model = self.treeview.get_model()
        if model is None:
            return
        mods = len(model)
        msg = self.format_mod_statusbar()
        self.emitter.emit("mods_updated", msg, mods)

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

    # TODO: strings
    @call_on_thread("working")
    def highlight_stale(self) -> None:
        stale = find_stale_mods(self.prefs.paths.config)
        func = StoredFunc(self._on_stale_mods_found, stale)
        self.thread_man.set_cleanup_func(func)

    def _server_timeout(self) -> None:
        dialog = ExceptionDialog(self.controller, server_timeout)
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
