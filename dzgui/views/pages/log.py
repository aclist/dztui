from typing import TYPE_CHECKING
from dzgui.const.constants import LOG_FILTERS
from dzgui.views.mixins.cursor_mixin import CursorMixin
from dzgui.views.mixins.help_menu_mixin import HelpMenuMixin
from dzgui.views.trees.tree_log import LogTreeView


import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa E402

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class Log(CursorMixin, HelpMenuMixin, Gtk.Box):  # type: ignore
    def __init__(self, controller: "Controller") -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        """
        NOTE: LogTreeView is kept in a separate ScrolledWindow so that
        checkboxes will be flush on bottom
        """
        self.scrolled = Gtk.ScrolledWindow()
        self.treeview = LogTreeView(controller)
        self.scrolled.add(self.treeview)

        self.check_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        for check in LOG_FILTERS:
            c = Gtk.CheckButton(label=check)
            self.check_bar.pack_start(c, False, False, 0)
            c.set_active(True)
            c.connect("clicked", self._on_checkbox_clicked)
        self.add(self.scrolled)
        self.add(self.check_bar)

        self.controller = controller
        self.controller.register_widget("logtreeview", self.treeview)
        self.emitter = controller.get_emitter()

        self.connect("key-press-event", self._on_esc_keypress)

    def _on_checkbox_clicked(self, checkbox: Gtk.CheckButton) -> None:
        label = checkbox.get_label()
        self.treeview.toggle_filter(label)

    def get_treeview(self) -> LogTreeView:
        return self.treeview

    def grab_content_area(self) -> None:
        self.treeview.grab_focus()
