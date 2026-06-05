import logging
import requests
import shutil
import subprocess
import tarfile
from typing import TYPE_CHECKING

from dzgui.const.constants import (
    APP_NAME,
    TMP_EXE,
    TMP_PATH,
    TMP_TARBALL,
)
from dzgui.strings import dialogs
from dzgui.managers.threading import call_on_thread, StoredFunc, ThreadingManager
from dzgui.views.dialogs.generic import ExceptionDialog, QuitDialog

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

logger = logging.getLogger(APP_NAME)


class UpdateManager:
    def __init__(self, controller: "Controller") -> None:

        self.thread_man = ThreadingManager(controller)
        self.controller = controller

    @call_on_thread(dialogs.fetching_update)
    def update_version(self, exe_path: str, url: str) -> None:
        try:
            res = requests.get(url)
            if res.status_code == 200:
                with open(TMP_TARBALL, "wb") as file:
                    file.write(res.content)
                with tarfile.open(TMP_TARBALL) as tar:
                    tar.extractall(TMP_PATH)

                shutil.copy(TMP_EXE, exe_path)

                proc = subprocess.run([exe_path, "self", "restore"])
                if proc.returncode == 0:
                    func = StoredFunc(self._on_update_success)
                    self.thread_man.set_cleanup_func(func, destroy_first=True)
                else:
                    msg = dialogs.failed_to_update
                    func = StoredFunc(self._on_update_failure, msg)
                    self.thread_man.set_cleanup_func(func, destroy_first=True)
        except Exception as e:
            func = StoredFunc(self._on_update_failure, e)
            self.thread_man.set_cleanup_func(func, destroy_first=True)
            logger.warning(e)

    def _on_update_success(self) -> None:
        msg = dialogs.update_success
        dialog = QuitDialog(self.controller, msg)
        dialog.run()

    def _on_update_failure(self, msg: str) -> None:
        dialog = ExceptionDialog(self.controller, msg)
        dialog.run()
