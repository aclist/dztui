import logging
import shutil

from dataclasses import dataclass
from packaging.version import Version
from pathlib import Path
from typing import TYPE_CHECKING

import dzgui.api.pefile as PeFile
import dzgui.api.servers as Servers
from dzgui.api.steam import get_remote_signatures, get_needs_update

from dzgui.api.mods import get_local_mod_ids
from dzgui.const.constants import (
    APP_NAME,
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    APPNAME_DAYZ,
    APPNAME_DAYZ_EXP,
)
from dzgui.const.enum import Preferences
from dzgui.init.proc import is_dayz_running, is_steam_running
from dzgui.managers.threading import call_on_thread, StoredFunc, ThreadingManager
from dzgui.util.format import format_mib
from dzgui.util.strings import dialog, server_timeout, checkmark
from dzgui.views.dialogs.generic import ExceptionDialog
from dzgui.views.dialogs.servers import ServerDetailsDialog, ServerModDialog

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.api.servers import A2SInfo, Record
    from dzgui.controllers.mc import Controller

logger = logging.getLogger(APP_NAME)


@dataclass(slots=True, frozen=True)
class Prerequisites:
    name: str
    appid: int
    local_version: Version
    remote_version: Version
    build: str
    binary_missing: bool
    required_space: float
    available_space: float
    passworded: bool
    dayz_running: bool
    steam_running: bool
    mods: list[str]


class ConnectionManager:
    def __init__(self, controller: "Controller") -> None:

        self.controller = controller
        self.thread_man = ThreadingManager(controller)

        self.appid: int
        self.record: Record

        self.remote_mod_ids: list[str] = []
        self.missing_mods: list[str] = []

    @call_on_thread(dialog.querying)
    def connect_by_id(self, _id: int, key: str) -> None:
        res = Servers.query_by_id(_id, key)
        self._prepare_connection(res)

    @call_on_thread(dialog.querying)
    def connect_by_ip(self, addr: str) -> None:
        res = Servers.query_by_ip(addr)
        self._prepare_connection(res)

    @call_on_thread(dialog.querying)
    def connect_by_record(self, record: Servers.Record) -> None:
        res = Servers.query_by_record(record)
        self._prepare_connection(res)

    def _prepare_connection(self, res: "A2SInfo") -> None:
        failure_func = StoredFunc(self._server_timeout)
        if res.get_info() is None:
            self.thread_man.set_cleanup_func(failure_func, destroy_first=True)
            return

        record = res.get_record()
        info = res.get_info()

        # NOTE: store metadata for later connection
        self.appid = info.game_id
        self.record = record

        builds = {APPID_DAYZ: APPNAME_DAYZ, APPID_DAYZ_EXP: APPNAME_DAYZ_EXP}
        build = builds[self.appid]
        binary_missing = False
        required_mib = 0.0
        free_mib = 0.0

        steam_path = Path(self.controller.query_config(Preferences.DEFAULT))
        local_version = PeFile.get_pretty_version(steam_path, info.game_id)
        if local_version is None:
            local_version = "0.0.0"
            binary_missing = True

        remote_mods: list[str, str, str] = []
        if res.is_modded():
            try:
                remote_mods = self._query_modlist(record)
                self.remote_mod_ids = [mod[1] for mod in remote_mods]
            except Exception as e:
                logger.warning(e)
                self.thread_man.set_cleanup_func(failure_func, destroy_first=True)
                return

            hashes = get_remote_signatures(self.remote_mod_ids)
            version_file = self.controller.get_prefs().paths.version
            self.missing_mods = get_needs_update(version_file, hashes)

            if local_version is not None:
                pefile_path = PeFile.get_pefile_path(steam_path, info.game_id)
                total, used, free = shutil.disk_usage(pefile_path)
                if len(self.missing_mods) > 0:
                    required_size = sum(int(row[2]) for row in self.missing_mods)
                    required_mib = format_mib(required_size)
                    free_mib = format_mib(required_size)

        dayz_running = is_dayz_running()
        steam_running = is_steam_running()
        # TODO: is dayz downloading

        prereqs = Prerequisites(
            name=info.server_name,
            appid=info.game_id,
            local_version=Version(local_version),
            remote_version=Version(info.version),
            build=build,
            binary_missing=binary_missing,
            required_space=required_mib,
            available_space=free_mib,
            passworded=info.password_protected,
            dayz_running=dayz_running,
            steam_running=steam_running,
            mods=remote_mods,
        )

        func = StoredFunc(self.controller.open_connection_assistant, prereqs)
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

    def connect(self) -> None:
        print(self.record.ip)
        print(self.record.gameport)
        print(self.appid)
        # TODO: convert mod ids to symlink hashes
        # steam api, concat mods

    # TODO: custom threading with glib idle callback
    def update_mods(self) -> None:
        print(self.missing_mods)
        # TODO: when downloading mods, create symlinks if missing
        # TODO: pack a final PreReq struct with pre-processed values
        # self.needs_update
        # then connect
        pass

    def update_and_connect(self) -> None:
        if len(self.missing_mods) > 0:
            self.update_mods()
        else:
            self.connect()
