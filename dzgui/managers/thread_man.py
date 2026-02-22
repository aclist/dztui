import inspect
import logging
import threading

from functools import wraps
from typing import Callable, Optional
from dzgui.views.dialogs.generic import WaitDialog


import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject  # noqa E402

logger = logging.getLogger(__name__)


def call_on_thread(dialog_str: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            self = args[0]
            stored = StoredFunc(func, *args, **kwargs)
            print("SELF", self)
            if not hasattr(self, "thread_man"):
                raise AttributeError
            if type(self.thread_man) is not ThreadingManager:
                raise TypeError(
                    "Attribute 'thread_man' must be of type 'ThreadingManager'"
                )
            self.thread_man.call_on_thread(dialog_str, stored)

        return wrapper

    return decorator


class StoredFunc:
    def __init__(self, func: Callable, *args, **kwargs) -> None:
        sig = inspect.signature(func)
        self.func = func
        self.bindings = sig.bind(*args, **kwargs)

    def call(self) -> None:
        self.func(*self.bindings.args, *self.bindings.kwargs)


class ThreadingManager:
    def __init__(self, parent: Gtk.Window) -> None:
        self.parent = parent
        self.jobs = 1
        self.cleanup_func = None
        self.alternate_statusbar = None

    def call_on_thread(self, dialog_str: str, func: StoredFunc) -> None:
        def callback() -> None:
            func.call()
            GLib.idle_add(self._destroy_on_idle)

        self.wait_dialog = WaitDialog(self.parent, dialog_str, jobs=self.jobs)
        self.wait_dialog.show_all()
        thread = threading.Thread(target=callback)
        thread.start()

    def set_job_count(self, jobs: int) -> None:
        self.jobs = jobs

    def increment_dialog(self) -> None:
        GLib.idle_add(self.wait_dialog.increment)

    def increment_dialog_with_str(self, text: str) -> None:
        GLib.idle_add(lambda: self.wait_dialog.increment(text))

    # TODO: this should not be delegated here
    def set_alternate_statusbar(self, msg: str) -> None:
        self.alternate_statusbar = msg

    def get_alternate_statusbar(self) -> Optional[str]:
        return self.alternate_statusbar

    def set_cleanup_func(self, func: StoredFunc) -> None:
        if type(func) not in (StoredFunc, type(None)):
            msg = f"Callback function '{func}' is not of type StoredFunc or None"
            logger.critical(msg)
            raise TypeError(msg)
        self.cleanup_func = func

    def get_cleanup_func(self) -> StoredFunc:
        return self.cleanup_func

    def _destroy_on_idle(self) -> None:
        self.wait_dialog.destroy()
        func = self.get_cleanup_func()
        if func is not None:
            func.call()
            self.set_cleanup_func(None)
