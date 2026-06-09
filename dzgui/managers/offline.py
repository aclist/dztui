from pathlib import Path
from typing import TYPE_CHECKING, Union

from dzgui.api.steam import launch_offline
from dzgui.const.enum import Preferences
from dzgui.managers.threading import call_on_thread, ThreadingManager
from dzgui.strings import dialogs
from dzgui.util.symlink import clone_symlinks

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class OfflineManager:
    def __init__(
        self,
        controller: "Controller",
        appid: int,
        mission: str = "",
        local_mods: Union[list[str], None] = None,
        custom_mods: Union[list[str], None] = None,
    ) -> None:
        super().__init__()

        self.controller = controller
        self.thread_man = ThreadingManager(controller)

        self.appid = appid
        self.mission_folder = mission
        self.local_mods = local_mods
        self.custom_mods = custom_mods

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
            clone_symlinks(Path(steam_path))
            combined_mods.extend(new_symlinks)

        launch_offline(client, self.appid, name, combined_mods, self.mission_folder)
