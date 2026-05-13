import logging
import os
import shutil
import time

from dataclasses import dataclass
from packaging.version import Version
from pathlib import Path
from typing import TYPE_CHECKING

import dzgui.api.pefile as PeFile
import dzgui.api.servers as Servers

from dzgui.api.steam import (
    connect,
    enqueue_mod,
    get_remote_signatures,
    get_needs_update,
)

from dzgui.api.mods import (
    get_mod_dir_size,
    get_local_mod_ids,
    get_local_mod_path,
    update_signatures,
)
from dzgui.const.constants import (
    APP_NAME,
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    APPNAME_DAYZ,
    APPNAME_DAYZ_EXP,
)
from dzgui.const.enum import NotebookPage, Preferences
from dzgui.init.proc import is_dayz_running, is_steam_running
from dzgui.managers.threading import call_on_thread, StoredFunc, ThreadingManager
from dzgui.strings.dialogs import waiting_for_launch, waiting_for_mods
from dzgui.strings.server_mods import checkmark, resync
from dzgui.util.format import format_mib
from dzgui.util.strings import dialog, server_timeout
from dzgui.util.symlink import rebuild_symlinks
from dzgui.views.dialogs.generic import ExceptionDialog
from dzgui.views.dialogs.servers import ServerDetailsDialog, ServerModDialog

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa E402

if TYPE_CHECKING:
    from dzgui.api.servers import A2SInfo, Record
    from dzgui.controllers.mc import Controller

logger = logging.getLogger(APP_NAME)


@dataclass(slots=True, frozen=True)
class SteamProcess:
    name: str
    is_running: bool


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
    steam_proc: SteamProcess
    mods: list[list[str]]
    game_mode: bool


class ConnectionManager:
    def __init__(self, controller: "Controller") -> None:

        self.controller = controller
        self.thread_man = ThreadingManager(controller)

        self.appid: int
        self.record: Record
        self.workshop: Path

        self.remote_mod_ids: list[str] = []
        self.missing_mods: list[tuple[str, str, int, int]] = []

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
        info = res.get_info()
        if info is None:
            self.thread_man.set_cleanup_func(failure_func, destroy_first=True)
            return

        self.history = res.as_row()
        record = res.get_record()

        # NOTE: store metadata for later connection
        self.appid = info.game_id
        self.record = record

        builds = {APPID_DAYZ: APPNAME_DAYZ, APPID_DAYZ_EXP: APPNAME_DAYZ_EXP}
        build = builds[self.appid]
        binary_missing = False
        required_mib = 0.0
        free_mib = 0.0

        steam_path = Path(self.controller.query_config(Preferences.DEFAULT))
        self.workshop = get_local_mod_path(steam_path)
        local_version = PeFile.get_pretty_version(steam_path, info.game_id)
        if local_version is None:
            local_version = "0.0.0"
            binary_missing = True

        prefs = self.controller.get_prefs()
        remote_mods: list[list[str]] = []
        if res.is_modded():
            try:
                remote_mods = self._query_modlist(record)
                self.remote_mod_ids = [mod[1] for mod in remote_mods]
            except Exception as e:
                logger.warning(e)
                self.thread_man.set_cleanup_func(failure_func, destroy_first=True)
                return

            hashes = get_remote_signatures(self.remote_mod_ids)
            version_file = prefs.paths.version
            self.missing_mods = get_needs_update(version_file, hashes)

            for mod in remote_mods:
                if any(mod[1] in tuple for tuple in self.missing_mods):
                    mod[2] = resync

            if local_version is not None:
                pefile_path = PeFile.get_pefile_path(steam_path, info.game_id)
                total, used, free = shutil.disk_usage(pefile_path)
                if len(self.missing_mods) > 0:
                    required_size = sum(row[2] for row in self.missing_mods)
                    required_mib = format_mib(required_size)
                    free_mib = format_mib(required_size)

        dayz_running = is_dayz_running()

        client_name = self.controller.get_steam_client_name()
        client = self.controller.query_config(Preferences.CLIENT)
        running = is_steam_running(client)
        steam_proc = SteamProcess(client_name, running)

        game_mode = prefs.is_game_mode

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
            steam_proc=steam_proc,
            mods=remote_mods,
            game_mode=game_mode,
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
        alpha_mods: list[list[str]] = [
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

    def _present_modlist_dialog(self, mods: list[list[str]]) -> None:
        dialog = ServerModDialog(self.controller, mods)
        dialog.run()

    def _present_details_dialog(self, details: Servers.Details) -> None:
        dialog = ServerDetailsDialog(self.controller, details)
        dialog.run()

    def _server_timeout(self) -> None:
        dialog = ExceptionDialog(self.controller, server_timeout)
        dialog.run()

    def _connect_steam(self) -> None:
        addr = f"{self.record.ip}:{self.record.gameport}"
        playername = self.controller.query_config(Preferences.NAME)
        client = self.controller.query_config(Preferences.CLIENT)
        rc = connect(client, addr, self.appid, playername, self.remote_mod_ids)
        if rc != 0:
            # TODO: log/pop the error
            func = StoredFunc(self.controller.update_status)
            self.thread_man.set_cleanup_func(func)
            return

        self.thread_man.show_cancel(False)
        self.thread_man.update_dialog(waiting_for_launch)
        while True:
            # TODO: check cancel event
            if self.controller.get_exit_event().is_set():
                # TODO: some facility to also close spawned steam process
                return
            if is_dayz_running():
                break
            time.sleep(1)

        func = StoredFunc(self._add_to_history_and_return)
        self.thread_man.set_cleanup_func(func)

    def _add_to_history_and_return(self) -> None:
        self.controller.add_to_history(self.history)
        self.controller.open_page(NotebookPage.SERVERS)

    def _update_mods(self, raise_window: bool) -> None:
        # NOTE: fast enqueue all mods in auto mode
        prefs = self.controller.get_prefs()

        for title, mod, stamp, size in self.missing_mods:
            # TODO: check cancel and exit events
            enqueue_mod(mod, self.appid)
            time.sleep(2)

        if raise_window is True:
            logger.info(f"Bringing window to foreground")
            GLib.idle_add(self.controller.present_window)

        for title, mod, stamp, size in self.missing_mods:
            mod_path = self.workshop / mod

            # NOTE: Steam updates mod chunks in parallel, will finish at the same time
            while mod_path.is_dir() is False:
                time.sleep(1)
            while True:
                if self.controller.get_exit_event().is_set():
                    return
                if self.controller.get_cancel_event().is_set():
                    self.controller.clear_cancel_event()
                    return
                cur_size = get_mod_dir_size(mod_path)
                if cur_size == size:
                    break
                time.sleep(1)

        update_signatures(self.missing_mods, prefs.paths.version)
        # TODO: just push steam path directly
        rebuild_symlinks(prefs.paths.config)
        self._connect_steam()

    @call_on_thread(waiting_for_mods, show_cancel=True)
    def update_and_connect(self, raise_window: bool) -> None:
        if len(self.missing_mods) > 0:
            self._update_mods(raise_window)
        else:
            self._connect_steam()
