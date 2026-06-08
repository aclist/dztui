from pathlib import Path
from typing import Self, Sequence, TYPE_CHECKING

from dzgui.util import css
import dzgui.api.pefile as PeFile
from dzgui.const.constants import APPID_DAYZ_EXP, APPNAME_DAYZ, APPNAME_DAYZ_EXP_HUMAN
from dzgui.const.enum import NotebookPage, Preferences
from dzgui.strings import offline
from dzgui.views.components.scrollable import NoOverlayScrolledWindow
from dzgui.views.components.frame import HeadingFrame
from dzgui.views.trees.tree_mods import OfflineModTreeView


import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.model.model_factory import FastInsertListStore


class GenericBox(Gtk.Box):
    def __init__(self, orientation: Gtk.Orientation) -> None:
        super().__init__(orientation=orientation)

    def extend(self, els: Sequence[Gtk.Widget]) -> None:
        for el in els:
            self.add(el)


class HBox(GenericBox):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)


class VBox(GenericBox):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)


class PageHeading(Gtk.Label):
    def __init__(self, label: str) -> None:
        super().__init__(label=label, halign=Gtk.Align.CENTER)

        css.add_class(self, "page-heading")


class FolderHBox(HBox):
    def __init__(self, btn_label: str) -> None:
        super().__init__()

        self.set_margin_start(10)
        self.set_margin_bottom(10)
        self.set_spacing(5)

        # TODO: use IconButton with folder-symbolic
        self.button = Gtk.Button(label=btn_label, halign=Gtk.Align.START)
        self.label = Gtk.Label()
        self.extend([self.button, self.label])

    def get_button(self) -> Gtk.Button:
        return self.button

    def set_label(self, label: str) -> None:
        self.label.set_label(label)


class ModFrame(HeadingFrame):
    def __init__(self, controller: "Controller", label: str) -> None:
        super().__init__(heading=label)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.tree = OfflineModTreeView(controller)
        self.tree.set_model(None)

        self.scrolled = NoOverlayScrolledWindow()
        self.scrolled.set_size_request(600, 400)
        self.scrolled.add(self.tree)
        self.status = Gtk.Label(
            halign=Gtk.Align.START, margin_start=5, margin_top=3, margin_bottom=3
        )

        self.vbox.pack_end(self.status, expand=False, fill=False, padding=0)
        self.vbox.pack_end(self.scrolled, expand=False, fill=False, padding=0)
        self.frame.add(self.vbox)

        sel = self.tree.get_selection()
        sel.connect("changed", self._on_selection_changed)

    def collapse_tree(self) -> None:
        self.scrolled.hide()

    def get_tree(self) -> OfflineModTreeView:
        return self.tree

    def pack_start(self, widget: Gtk.Widget) -> None:
        self.vbox.pack_start(widget, expand=False, fill=False, padding=5)

    def set_model(self, model: "FastInsertListStore") -> None:
        self.tree.set_model(model)
        self.tree.mod_man.store = model
        self.set_cursor()

    def _on_selection_changed(self, sel: Gtk.TreeSelection) -> None:
        model, rows = sel.get_selected_rows()
        status = f"Mods selected: {len(rows)}"
        self.status.set_label(status)

    def set_cursor(self) -> None:
        path = Gtk.TreePath.new_from_indices([0])
        self.tree.set_cursor(path)


class CustomModFrame(ModFrame):
    def __init__(self, controller: "Controller", heading: str) -> None:
        super().__init__(controller, heading)

        self.controller = controller
        self.custom_hbox = FolderHBox(offline.custom_button)
        self.custom_hbox.get_button().connect("clicked", self._on_custom_button_clicked)

        self.pack_start(self.custom_hbox)

    def _on_custom_button_clicked(self, button: Gtk.Button) -> None:
        # TODO: recycle for mission folder
        # TODO: propagate results back to parent
        folder = self.controller.set_custom_folder()
        if folder is not None:
            # TODO: CustomModManager
            self.custom_hbox.set_label(str(folder))


class RadioFrame(HeadingFrame):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(heading=offline.version)

        self.controller = controller

        self.dayz = Gtk.RadioButton.new_with_label(None, APPNAME_DAYZ)
        self.dayz_exp = Gtk.RadioButton.new_with_label_from_widget(
            self.dayz, APPNAME_DAYZ_EXP_HUMAN
        )

        self.radio_box = HBox()
        self.radio_box.extend([self.dayz, self.dayz_exp])
        self.radio_box.set_margin_start(10)
        self.radio_box.set_margin_bottom(5)

        self.frame.add(self.radio_box)

        default_steam_path = self.controller.query_config(Preferences.DEFAULT)
        steam_path = Path(default_steam_path)
        dayz_exp = PeFile.get_pretty_version(steam_path, APPID_DAYZ_EXP)
        if dayz_exp is None:
            self.dayz_exp.set_sensitive(False)


class OfflineLoader(Gtk.Box):
    def __init__(self, controller: "Controller"):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            margin_start=10,
            margin_end=10,
        )

        # TODO: wrap entire page in scrollable, see preconnect dialog
        # TODO: spacing between inner and outer scrollbars
        self.controller = controller
        self.controller.register_widget("offline_loader", self)

        self.add(PageHeading(offline.heading))

        # TODO: descriptive text here explaining how this area works
        self.local_frame = ModFrame(controller, offline.local_frame)
        self.custom_frame = CustomModFrame(controller, offline.custom_frame)

        self.mission_hbox = FolderHBox(offline.mission_button)
        self.mission_frame = HeadingFrame.new_with_widget_and_label(
            self.mission_hbox, offline.mission_frame
        )

        self.radio_frame = RadioFrame(controller)
        # HeadingFrame.new_with_widget_and_label(self.radio_box, offline.version)

        # TODO: abstraction
        self.scrollable = Gtk.ScrolledWindow(
            vexpand=True, propagate_natural_height=True
        )
        # TODO: use same button anchoring logic as preconnect dialog
        self.content_box = VBox()
        self.content_box.set_spacing(5)
        self.content_box.extend(
            [
                self.local_frame,
                self.custom_frame,
                self.mission_frame,
                self.radio_frame,
            ]
        )

        self.scrollable.add(self.content_box)
        self.add(self.scrollable)

        # TODO: use ModelFactory
        # TODO: suppress symlink column
        self.custom_tree = OfflineModTreeView(controller)

        # TODO: share ConnectBox class with preconnect dialog
        self.button_box = HBox()
        self.back = Gtk.Button()
        self.ok = Gtk.Button()
        self.back.connect("clicked", self._on_back_clicked)
        self.ok.connect("clicked", self._on_ok_clicked)
        self.connect("key-press-event", self._on_keypress)

        self.button_box.extend([self.back, self.ok])

    def _on_keypress(self, widget: Self, event: Gdk.EventKey) -> None:
        # TODO: consider dropping this
        if event.keyval == Gdk.KEY_Escape:
            self.back.emit("clicked")

    def populate(self, store: "FastInsertListStore") -> None:
        self.local_frame.set_model(store)
        # TODO: toggle if empty model, show warning label
        # TODO: suppress trees if there are no mods
        self.custom_frame.collapse_tree()

    def _on_back_clicked(self, button: Gtk.Button) -> None:
        # FIXME: returns to server page and not parent mod page
        # consider using a toggle button instead, and suppressing statusbar
        self.controller.open_page(NotebookPage.SERVERS)

    def _on_ok_clicked(self, button: Gtk.Button) -> None:
        """
        - collect symlinks to selected mods
            cf. rebuild_symlinks()
        - create symlinks for custom mods
        - collect appid
        - collect mission folder
        """
        pass
