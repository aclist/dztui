import inspect
import logging
import threading
from typing import Any, Literal, TYPE_CHECKING

from functools import wraps
from typing import Callable

from dzgui.const.constants import APP_NAME
from dzgui.views.dialogs.generic import WaitDialog

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa E402

logger = logging.getLogger(APP_NAME)


def call_on_thread(
    dialog_str: str, show_dialog: bool = True, show_cancel: bool = False
) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> None:
            self = args[0]
            stored = StoredFunc(func, *args, **kwargs)
            if not hasattr(self, "thread_man"):
                raise AttributeError
            if type(self.thread_man) is not ThreadingManager:
                raise TypeError(
                    "Attribute 'thread_man' must be of type 'ThreadingManager'"
                )
            self.thread_man.call_on_thread(dialog_str, stored, show_dialog, show_cancel)

        return wrapper

    return decorator


class StoredFunc:
    def __init__(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        sig = inspect.signature(func)
        self.func = func
        self.bindings = sig.bind(*args, **kwargs)

    def call(self) -> None:
        self.func(*self.bindings.args, *self.bindings.kwargs)


class ThreadingManager:
    def __init__(self, controller: "Controller") -> None:
        self.controller = controller
        self.jobs = 1
        self.cleanup_func: StoredFunc | None = None
        self.destroy_first = False

    def call_on_thread(
        self,
        dialog_str: str,
        func: StoredFunc,
        show_dialog: bool = True,
        show_cancel: bool = False,
    ) -> None:
        def callback() -> None:
            func.call()
            GLib.idle_add(self._destroy_on_idle)

        if show_dialog:
            self.wait_dialog = WaitDialog(
                self.controller, dialog_str, jobs=self.jobs, show_cancel=show_cancel
            )
            self.wait_dialog.show_all()

        thread = threading.Thread(target=callback)
        thread.start()

    def set_job_count(self, jobs: int) -> None:
        self.jobs = jobs

    def update_dialog(self, msg: str) -> None:
        GLib.idle_add(lambda: self.wait_dialog.update_text(msg))

    def increment_dialog(self) -> None:
        GLib.idle_add(self.wait_dialog.increment)

    def increment_dialog_with_str(self, text: str) -> None:
        GLib.idle_add(lambda: self.wait_dialog.increment(text))

    def set_cleanup_func(
        self, func: StoredFunc | None, destroy_first: bool = False
    ) -> None:
        if type(func) not in (StoredFunc, type(None)):
            msg = f"Callback function '{func}' is not of type StoredFunc or None"
            logger.critical(msg)
            raise TypeError(msg)
        self.destroy_first = destroy_first
        self.cleanup_func = func

    def get_cleanup_func(self) -> StoredFunc | None:
        return self.cleanup_func

    def destroy_dialog(self) -> None:
        if hasattr(self, "wait_dialog"):
            self.wait_dialog.destroy()

    def _destroy_on_idle(self) -> Literal[False]:
        if self.destroy_first:
            self.destroy_dialog()

        func = self.get_cleanup_func()
        if func is not None:
            func.call()
            self.set_cleanup_func(None)
        if not self.destroy_first:
            self.destroy_dialog()

        return False

    def get_wait_dialog(self) -> WaitDialog:
        return self.wait_dialog

    def show_cancel(self, state: bool) -> None:
        GLib.idle_add(self.wait_dialog.show_cancel, state)
