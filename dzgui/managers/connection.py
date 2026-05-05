import logging
import shutil

from pathlib import Path
from typing import Union, TYPE_CHECKING

import dzgui.api.pefile as PeFile
import dzgui.api.servers as Servers
from dzgui.api.steam import get_remote_signatures, get_needs_update

from dzgui.api.mods import get_local_mod_ids
from dzgui.const.constants import APP_NAME
from dzgui.const.enum import Preferences
from dzgui.managers.threading import call_on_thread, StoredFunc, ThreadingManager
from dzgui.util.strings import dialog, server_timeout, checkmark
from dzgui.views.dialogs.generic import ExceptionDialog
from dzgui.views.dialogs.servers import ServerDetailsDialog, ServerModDialog

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.api.servers import PreReqs
    from dzgui.controllers.mc import Controller

logger = logging.getLogger(APP_NAME)


class ConnectionManager:
    def __init__(self, controller: "Controller") -> None:

        self.controller = controller
        self.thread_man = ThreadingManager(controller)

    @call_on_thread(dialog.querying)
    def connect_by_id(self, _id: int, key: str) -> None:
        res = Servers.query_by_id(_id, key, full=True)
        self._prepare_connection(res)

    @call_on_thread(dialog.querying)
    def connect_by_ip(self, addr: str) -> None:
        res = Servers.query_by_ip(addr, full=True)
        self._prepare_connection(res)

    @call_on_thread(dialog.querying)
    def connect_by_record(self, record: Servers.Record) -> None:
        res = Servers.query_by_record(record, full=True)
        self._prepare_connection(res)

    def _prepare_connection(self, res: Union["PreReqs", None]) -> None:
        failure_func = StoredFunc(self._server_timeout)
        if res is None:
            self.thread_man.set_cleanup_func(failure_func, destroy_first=True)
            return

        record = res.record
        try:
            remote_mods = self._query_modlist(record)
            remote_mod_ids = [mod[1] for mod in remote_mods]
        except Exception as e:
            print(e)
            self.thread_man.set_cleanup_func(failure_func, destroy_first=True)
            return

        steam_path = Path(self.controller.query_config(Preferences.DEFAULT))

        hashes = get_remote_signatures(remote_mod_ids)
        version_file = self.controller.get_prefs().paths.version
        needs_update = get_needs_update(version_file, hashes)

        # TODO: store mods that need update in class object for referencing later
        # TODO: store remote destination to connect to

        # missing mods should be the totality of all mods with no signature
        # missing = get_missing_mods(local_mod_ids, remote_mod_ids)
        # print(missing)
        # TODO: when downloading mods, create symlinks if missing

        # TODO: get missing mod sizes, warn if not enough space
        info = res.source
        try:
            dayz_path = PeFile.get_pefile_path(steam_path, info.game_id)
            # TODO: handle missing path; do not calculate size if appid is missing
            total, used, free = shutil.disk_usage(dayz_path)
            if len(needs_update) > 0:
                # TODO: generic mib function
                required_size = sum(int(row[2]) for row in needs_update)
                required_mib = round(required_size / (1024**2), 3)
                free_mib = round(free / (1024**2), 3)
                print(required_mib)
                print(free_mib)
        except Exception:
            # TODO: if this fails, need to show missing build warning, not failure func
            # build up list of warnings/errors
            # logger.warning(e)
            self.thread_man.set_cleanup_func(failure_func, destroy_first=True)

        # TODO: number separator func
        # TODO: pack a final PreReq struct with pre-processed values

        # TODO: connection assistant only receives user-facing warnings and list of mods
        func = StoredFunc(self.controller.open_connection_assistant, res, remote_mods)
        self.thread_man.set_cleanup_func(func, destroy_first=True)

    @call_on_thread(dialog.querying)
    def query_details(self, record: Servers.Record) -> None:
        details = Servers.get_details(record)
        if details.success is False:
            self.thread_man.set_cleanup_func(
                StoredFunc(self._server_timeout), destroy_first=True
            )
            return
        self.thread_man.set_cleanup_func(
            StoredFunc(self._present_details_dialog, details), destroy_first=True
        )

    def _query_modlist(self, record: Servers.Record) -> list[list[str]]:
        mods = Servers.get_rules(record)
        steam_path = self.controller.query_config(Preferences.DEFAULT)
        local = get_local_mod_ids(steam_path)
        alpha_mods = [
            [
                mod.name,
                str(mod.workshop_id),
                checkmark if mod.workshop_id in local else "",
            ]
            for mod in mods
        ]
        alpha_mods.sort(key=lambda x: x[0])
        return alpha_mods

    @call_on_thread(dialog.querying)
    def query_modlist_and_present(self, record: Servers.Record) -> None:
        try:
            mods = self._query_modlist(record)
        except Exception:
            self.thread_man.set_cleanup_func(
                StoredFunc(self._server_timeout), destroy_first=True
            )
            return
        self.thread_man.set_cleanup_func(
            StoredFunc(self._present_modlist_dialog, mods),
            destroy_first=True,
        )

    def _present_modlist_dialog(self, mods: list[str]) -> None:
        dialog = ServerModDialog(self.controller, mods)
        dialog.run()

    def _present_details_dialog(self, details: Servers.Details) -> None:
        dialog = ServerDetailsDialog(self.controller, details)
        dialog.run()

    def _server_timeout(self) -> None:
        dialog = ExceptionDialog(self.controller, server_timeout)
        dialog.run()

    def update_mods(self) -> None:
        # self.needs_update
        pass

    def connect(self) -> None:
        # steam api, concat mods
        pass
