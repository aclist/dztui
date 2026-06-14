import logging
import time
from pathlib import Path
from typing import Callable, TYPE_CHECKING, Union

import dzgui.api.pefile as PeFile
from dzgui.api.mods import is_mission, get_custom_mods
from dzgui.api.steam import launch_offline
from dzgui.const.constants import APP_NAME, APPID_DAYZ_EXP
from dzgui.const.enum import Preferences
from dzgui.init.proc import is_dayz_running
from dzgui.managers.threading import call_on_thread, StoredFunc, ThreadingManager
from dzgui.model.model_factory import ModelFactory
from dzgui.strings import dialogs
from dzgui.util.symlink import create_custom_symlinks, clone_symlinks, symlink_mission
from dzgui.views.dialogs.filepicker import FolderPicker

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.model.model_factory import FastInsertListStore

logger = logging.getLogger(APP_NAME)


class OfflineManager:
    def __init__(
        self,
        controller: "Controller",
    ) -> None:
        super().__init__()

        self.controller = controller
        self.emitter = controller.get_emitter()
        self.thread_man = ThreadingManager(controller)

        self.appid: int
        self.mission_folder: str
        self.local_mods: list[str] | None
        self.custom_mods: list[str] | None

    def get_mission(self) -> None:
        folder = self.open_folderpicker(dialogs.mission_dialog)
        if folder is None:
            return
        is_valid = is_mission(folder)
        self.emitter.emit("custom_mission_loaded", str(folder), is_valid)

    def find_custom_mods(self, callback: Callable) -> None:
        folder = self.open_folderpicker(dialogs.custom_mod_dialog)
        window = self.controller.get_window()
        window.set_sensitive(False)
        if folder is None:
            window.set_sensitive(True)
            return
        # NOTE: starts spinner in calling UI
        callback()
        self.parse_custom_mods(folder)

    @call_on_thread(dialogs.parsing_mods, show_dialog=False)
    def parse_custom_mods(self, folder: str) -> None:
        mods = get_custom_mods(Path(folder))
        store = ModelFactory().make_mod_store()
        store.extend(mods)
        func = StoredFunc(self.post_mod_loading, store, folder)
        self.thread_man.set_cleanup_func(func)

    def post_mod_loading(self, store: "FastInsertListStore", folder: str) -> None:
        window = self.controller.get_window()
        window.set_sensitive(True)
        self.emitter.emit("custom_mods_loaded", store, folder)

    @call_on_thread(dialogs.waiting_for_launch)
    def launch(
        self,
        appid: int,
        mission: str,
        local_mods: list[str],
        custom_folder: str,
        custom_mods: list[str],
    ) -> None:

        # NOTE: local_mods and custom_mods are lists of symlinks
        client = self.controller.query_config(Preferences.CLIENT)
        name = self.controller.query_config(Preferences.NAME)
        steam_path = self.controller.query_config(Preferences.DEFAULT)

        combined_mods: list[str] = []

        if len(local_mods) > 0:
            combined_mods.extend(local_mods)

        if len(custom_mods) > 0:
            new_symlinks = create_custom_symlinks(
                Path(steam_path), Path(custom_folder), custom_mods
            )
            combined_mods.extend(new_symlinks)

        if len(mission) > 0:
            relative_link = symlink_mission(Path(steam_path), mission)

        launch_offline(client, appid, name, combined_mods, relative_link)
        while True:
            if is_dayz_running():
                break
            time.sleep(1)

    def open_folderpicker(self, title: str) -> Union["Path", None]:
        picker = FolderPicker(self.controller.get_window(), title)
        folder = picker.pick_folder()
        picker.destroy()
        return folder

    def has_dayz_exp(self) -> bool:
        try:
            default_steam_path = self.controller.query_config(Preferences.DEFAULT)
            steam_path = Path(default_steam_path)
            dayz_exp = PeFile.get_pretty_version(steam_path, APPID_DAYZ_EXP)
            if dayz_exp is None:
                return False
            return True
        except Exception as e:
            logger.warning(e)
            return False
