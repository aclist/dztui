from pathlib import Path
from typing import Union

from dzgui.api.steam import launch_offline
from dzgui.const.enum import Preferences
from dzgui.managers.threading import call_on_thread, ThreadingManager
from dzgui.strings import dialogs
from dzgui.util.symlinks import clone_symlinks


class OfflineManager:
    def __init__(
        self,
        appid: int,
        mission: Union[Path, None] = None,
        local_mods: Union[list[str], None] = None,
        custom_mods: Union[list[str], None] = None,
    ) -> None:
        super().__init__()

        self.thread_man = ThreadingManager()

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
            combined_mods.extend(self.local_mods)
            combined_mods.extend(new_symlinks)

            # TODO: cf. rebuild_symlinks

            clone_symlinks(Path(steam_path))
            launch_offline(client, self.appid, name, combined_mods)
