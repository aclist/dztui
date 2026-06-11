from pathlib import Path
from typing import TYPE_CHECKING, Union

from dzgui.api.mods import is_mission, get_custom_mods
from dzgui.api.steam import launch_offline
from dzgui.const.enum import Preferences
from dzgui.managers.threading import call_on_thread, StoredFunc, ThreadingManager
from dzgui.model.model_factory import ModelFactory
from dzgui.strings import dialogs
from dzgui.util.symlink import clone_symlinks
from dzgui.views.dialogs.filepicker import FolderPicker

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


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
        folder = self.open_folderpicker()
        if folder is None:
            return
        is_valid = is_mission(folder)
        # TODO: stop storing values in here
        if is_valid:
            # TODO: str
            self.mission_folder = str(folder)
        self.emitter.emit("custom_mission_loaded", str(folder), is_valid)

    def get_custom_mods(self, local_mods: list[str]) -> None:
        folder = self.open_folderpicker()
        if folder is None:
            return
        self.parse_custom_mods(local_mods, folder)

    @call_on_thread(dialogs.parsing_mods)
    def parse_custom_mods(self, local_mods: list[str], folder: str) -> None:
        mods = get_custom_mods(Path(folder))
        store = ModelFactory().make_mod_store()
        store.extend(mods)

        has_duplicates = False
        seen = set()
        for row in store:
            mod_id = row[1]
            if mod_id in seen:
                row[-1]=True
                has_duplicates = True
            seen.add(mod_id)

        func = StoredFunc(lambda: self.emitter.emit("custom_mods_loaded", store, folder, has_duplicates))
        self.thread_man.set_cleanup_func(func)

    def setup(
        self,
        appid: int,
        mission: str = "",
        local_mods: list[str] | None = None,
        custom_mods: list[str] | None = None,
    ) -> None:

        self.appid = appid
        self.local_mods = local_mods
        self.custom_mods = custom_mods

        self.launch()

    @call_on_thread(dialogs.waiting_for_launch)
    def launch(self) -> None:
        client = self.controller.query_config(Preferences.CLIENT)
        name = self.controller.query_config(Preferences.NAME)
        steam_path = self.controller.query_config(Preferences.DEFAULT)

        new_symlinks: list[str] = []

        combined_mods: list[str] = []
        if self.local_mods is not None:
            combined_mods.extend(self.local_mods)

        if self.custom_mods is not None:
            # TODO: new function that creates symlinks in game path
            # based on selected mods
            clone_symlinks(Path(steam_path))
            combined_mods.extend(new_symlinks)

        launch_offline(client, self.appid, name, combined_mods, self.mission_folder)

    def open_folderpicker(self) -> Union["Path", None]:
        picker = FolderPicker(self.controller.get_window())
        folder = picker.pick_folder()
        picker.destroy()
        return folder
