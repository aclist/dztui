import logging
import shutil
import time

from dataclasses import dataclass
from packaging.version import Version
from pathlib import Path
from typing import TYPE_CHECKING

import dzgui.api.pefile as PeFile
import dzgui.api.servers as Servers
from dzgui.api.shortcuts import Shortcuts

from dzgui.api.steam import (
    connect,
    get_app_allows_downloads,
    get_app_name,
    get_needs_update,
    get_remote_signatures,
    get_running_app,
    load_to_menu,
    subscribe,
)

from dzgui.api.mods import (
    get_mod_dir_size,
    get_local_mod_ids,
    get_local_mod_path,
    update_signatures,
)
from dzgui.const.constants import (
    API_RATE_LIMIT,
    APP_NAME,
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    APPNAME_DAYZ,
    APPNAME_DAYZ_EXP_HUMAN,
)
from dzgui.api.steam import is_dayz_running
from dzgui.const.enum import NotebookPage, Preferences
from dzgui.init.proc import is_steam_running
from dzgui.managers.threading import call_on_thread, StoredFunc, ThreadingManager
from dzgui.strings.dialogs import (
    waiting_for_launch,
    waiting_for_mods,
    waiting_for_directories,
)
from dzgui.strings import kb
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
    is_last_server: bool
    invalid_mods: list[tuple[str, str]]
    allows_downloads: tuple[bool, str]


class ConnectionManager:
    def __init__(self, controller: "Controller") -> None:

        self.controller = controller
        self.thread_man = ThreadingManager(controller)

        self.appid: int
        self.record: Record
        self.workshop: Path

        self.client: str
        self.remote_mod_ids: list[str] = []
        self.missing_mods: list[tuple[str, str, int, int]] = []

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

        try:
            self.history = res.as_row()
        except Exception:
            self.thread_man.set_cleanup_func(failure_func, destroy_first=True)
            return

        record = res.get_record()

        # NOTE: store metadata for later connection
        self.appid = info.game_id
        self.record = record

        builds = {APPID_DAYZ: APPNAME_DAYZ, APPID_DAYZ_EXP: APPNAME_DAYZ_EXP_HUMAN}
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
                remote_mods, missing_mods = self._query_modlist(record)
                self.missing_mods = missing_mods
                self.remote_mod_ids = [mod[1] for mod in remote_mods]
            except Exception as e:
                logger.warning(e)
                self.thread_man.set_cleanup_func(failure_func, destroy_first=True)
                return

            if local_version is not None:
                pefile_path = PeFile.get_pefile_path(steam_path, info.game_id)
                total, used, free = shutil.disk_usage(pefile_path)
                if len(self.missing_mods) > 0:
                    required_size = sum(row[2] for row in self.missing_mods)
                    required_mib = format_mib(required_size)
                    free_mib = format_mib(free)

        dayz_running = is_dayz_running()

        running_app = get_running_app()
        if running_app is not None:
            allows_dl = get_app_allows_downloads(steam_path, running_app)
            running_app_name = get_app_name(running_app)
            # NOTE: for out-of-range appid, assume NSG.
            # dzgui.api.steam.get_app_name() will return None
            if running_app_name is None:
                s = Shortcuts(steam_path)
                # NOTE: returns "Unknown" if unparseable
                running_app_name = s.find_appname_by_unsigned_id(running_app)
            allows_downloads = (allows_dl, running_app_name)
        else:
            allows_downloads = (True, "")

        client_name = self.controller.get_steam_client_name()
        client = self.controller.query_config(Preferences.CLIENT)
        running = is_steam_running(client)
        steam_proc = SteamProcess(client_name, running)
        self.client = client

        game_mode = prefs.is_game_mode

        is_last = self.is_last_server()

        # TODO: strings
        invalid_mods = [
            (mod[0], mod[1]) for mod in remote_mods if mod[2] == "Invalid mod"
        ]

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
            is_last_server=is_last,
            invalid_mods=invalid_mods,
            allows_downloads=allows_downloads,
        )

        func = StoredFunc(self.controller.open_connection_assistant, prereqs)
        self.thread_man.set_cleanup_func(func, destroy_first=True)

    def is_last_server(self) -> bool:
        prefs = self.controller.get_prefs()
        history = prefs.paths.history
        try:
            lines = history.read_text().splitlines()
            last = lines[-1]
            current = Servers.record_to_fqip(self.record)
            return last == current
        except Exception:
            return False

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

    def _query_modlist(
        self, record: Servers.Record
    ) -> tuple[list[list[str]], list[tuple[str, str, int, int]]]:
        mods = Servers.get_rules(record)
        steam_path = self.controller.query_config(Preferences.DEFAULT)
        local = get_local_mod_ids(Path(steam_path))

        alpha_mods: list[list[str]] = [
            [
                mod.name,
                str(mod.workshop_id),
                checkmark if mod.workshop_id in local else "",
            ]
            for mod in mods
        ]
        alpha_mods.sort(key=lambda x: x[0])

        prefs = self.controller.get_prefs()
        version_file = prefs.paths.version

        remote_mod_ids = [mod[1] for mod in alpha_mods]
        hashes = get_remote_signatures(remote_mod_ids)
        missing_mods = get_needs_update(version_file, hashes)
        for mod in alpha_mods:
            if any(mod[1] in tuple for tuple in missing_mods):
                mod[2] = resync
        for mod in alpha_mods:
            # NOTE: if the mod is neither synched or out of date, it is a malformed mod
            if mod[2] == "":
                # TODO: strings
                mod[2] = "Invalid mod"

        return alpha_mods, missing_mods

    @call_on_thread(dialog.querying)
    def query_modlist_and_present(self, record: Servers.Record) -> None:
        try:
            mods, missing_mods = self._query_modlist(record)
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
        dialog.set_secondary_text(kb.DZG_006)
        dialog.run()

    def _connect_steam(self, menu_only: bool) -> None:
        addr = f"{self.record.ip}:{self.record.gameport}"
        playername = self.controller.query_config(Preferences.NAME)
        if menu_only:
            rc = load_to_menu(self.client, self.appid, playername, self.remote_mod_ids)
        else:
            rc = connect(self.client, addr, self.appid, playername, self.remote_mod_ids)
        if rc != 0:
            # TODO: log/pop the error
            func = StoredFunc(self.controller.update_status)
            self.thread_man.set_cleanup_func(func)
            return

        self.thread_man.update_dialog(waiting_for_launch)
        while True:
            # FIXME: cancel should not be visible here per setting above
            if self.controller.is_cancel_pending():
                # TODO: some facility to also close spawned steam process
                return
            if is_dayz_running():
                break
            time.sleep(1)

        func = StoredFunc(self._add_to_history_and_return)
        self.thread_man.set_cleanup_func(func)

    def _add_to_history_and_return(self) -> None:
        self.controller.add_to_history(self.history, self.record)
        self.controller.open_page(NotebookPage.SERVERS)

    def _update_mods(self, menu_only: bool = False) -> None:
        prefs = self.controller.get_prefs()
        config_man = self.controller.get_config_man()
        key = config_man.lookup(Preferences.STEAM)

        for title, mod, stamp, size in self.missing_mods:
            if self.controller.is_cancel_pending():
                return
            subscribe(key, int(mod))
            time.sleep(API_RATE_LIMIT)

        self.thread_man.update_dialog(waiting_for_directories)
        for title, mod, stamp, size in self.missing_mods:
            mod_path = self.workshop / mod

            # NOTE: Steam updates mod chunks in parallel, will finish at the same time
            while mod_path.is_dir() is False:
                if self.controller.is_cancel_pending():
                    return
                time.sleep(1)
            while True:
                if self.controller.is_cancel_pending():
                    return
                cur_size = get_mod_dir_size(mod_path)
                if cur_size == size:
                    break
                time.sleep(1)

        update_signatures(self.missing_mods, prefs.paths.version)
        rebuild_symlinks(prefs.paths.config)

        # NOTE: update table status in main loop
        self.thread_man.update_emitter("all_mods_synched")

        # TODO: just push steam path directly
        self._connect_steam(menu_only)

    @call_on_thread(waiting_for_mods, show_cancel=True)
    def update_and_connect(self, menu_only: bool = False) -> None:
        if len(self.missing_mods) > 0:
            self._update_mods(menu_only)
        else:
            self._connect_steam(menu_only)
