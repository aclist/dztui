from __future__ import annotations
from pathlib import Path
from typing import Self, Sequence, TYPE_CHECKING, Union

from dzgui.util import css
import dzgui.api.pefile as PeFile
from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    APPNAME_DAYZ,
    APPNAME_DAYZ_EXP_HUMAN,
    FOLDER,
)
from dzgui.const.enum import NotebookPage, Preferences
from dzgui.managers.offline import OfflineManager
from dzgui.strings import generic, offline
from dzgui.views.components.buttons import IconTextButton
from dzgui.views.components.frame import HeadingFrame
from dzgui.views.components.scrollable import NoOverlayScrolledWindow
from dzgui.views.trees.tree_mods import OfflineModTreeView


import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter
    from dzgui.model.model_factory import FastInsertListStore


class GenericBox(Gtk.Box):
    def __init__(self, orientation: Gtk.Orientation, spacing: int = 0) -> None:
        super().__init__(orientation=orientation, spacing=spacing)

    def extend(self, els: Sequence[Gtk.Widget]) -> None:
        for el in els:
            self.add(el)


class HBox(GenericBox):
    def __init__(self, spacing: int = 0) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing)


class VBox(GenericBox):
    def __init__(self, spacing: int = 0) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)


class PageHeading(Gtk.Label):
    def __init__(self, label: str) -> None:
        super().__init__(label=label, halign=Gtk.Align.CENTER)

        css.add_class(self, "page-heading")


class FolderHBox(HBox):
    def __init__(self, btn_label: str) -> None:
        super().__init__(spacing=10)

        self.set_margin_start(10)
        self.set_margin_end(10)
        self.set_margin_bottom(5)

        # TODO: alternate class for left-aligned icons
        self.button = IconTextButton(FOLDER, btn_label)
        self.button.set_halign(Gtk.Align.START)
        self.button.set_image_position(Gtk.PositionType.LEFT)

        self.scrolled_label = Gtk.ScrolledWindow(propagate_natural_width=True, halign=Gtk.Align.START)
        self.label = Gtk.Label()
        self.scrolled_label.add(self.label)
        self.extend([self.button, self.scrolled_label])

    def get_button(self) -> Gtk.Button:
        return self.button

    def set_label(self, label: str) -> None:
        # TODO: strings
        prefix = "Current folder: "
        self.label.set_label(prefix + label)

    def hide_label(self) -> None:
        self.label.hide()


class ModFrame(HeadingFrame):
    def __init__(self, parent: OfflineLoader, controller: "Controller", label: str) -> None:
        super().__init__(heading=label)

        self.parent = parent
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.tree = OfflineModTreeView(controller)
        self.tree.set_model(None)
        self.tree.set_valign(Gtk.Align.FILL)

        self.scrolled = NoOverlayScrolledWindow()
        self.scrolled.set_margin_end(5)
        self.scrolled.set_vexpand(True)
        self.scrolled.add(self.tree)

        self.status = Gtk.Label(
            halign=Gtk.Align.START, margin_start=5, margin_top=3, margin_bottom=3
        )

        self.tree_vbox = VBox()
        self.tree_vbox.extend([self.scrolled, self.status])

        self.vbox.pack_end(self.tree_vbox, expand=True, fill=True, padding=3)
        self.frame.add(self.vbox)

        sel = self.tree.get_selection()
        sel.connect("changed", self._on_selection_changed)

        # TODO: inherit icons from warnings area in preconnect dialog
        self.error_label = Gtk.Label(label="No mods found", halign=Gtk.Align.START, margin_start=10, margin_bottom=5)
        self.vbox.pack_end(self.error_label, expand=True, fill=True, padding=3)

    def set_error(self, msg: str) -> None:
        self.error_label.set_label(msg)
        self.error_label.show()

    def hide_errors(self) -> None:
        self.error_label.hide()

    def start_empty(self) -> None:
        self.error_label.show()
        self.collapse_tree()

    def hide_all(self) -> None:
        self.error_label.hide()
        self.collapse_tree()

        # TODO: warnings area
        # name collision within custom mods

    def get_mods(self) -> list[str]:
        model, treeiters = self.tree.get_selection().get_selected_rows()
        if model is None:
            return []
        return [model[_iter][1] for _iter in treeiters]

    def collapse_tree(self) -> None:
        self.tree_vbox.hide()

    def get_tree(self) -> OfflineModTreeView:
        return self.tree

    def pack(self, widget: Gtk.Widget) -> None:
        self.vbox.pack_start(widget, expand=False, fill=False, padding=5)

    def set_model(self, model: Union["FastInsertListStore", None]) -> None:
        self.tree.set_model(model)
        self.tree.mod_man.store = model
        self.set_cursor()

    def _on_selection_changed(self, sel: Gtk.TreeSelection) -> None:
        model, rows = sel.get_selected_rows()
        if len(rows) == 0:
            status = generic.selectable_tree
        else:
            status = f"Mods selected: {len(rows)}"
        self.status.set_label(status)
        self.parent.check_button()

    def set_cursor(self) -> None:
        path = Gtk.TreePath.new_from_indices([0])
        self.tree.set_cursor(path)
        self.tree.get_selection().unselect_all()


class CustomModFrame(ModFrame):
    def __init__(
        self, parent: OfflineLoader, controller: "Controller", heading: str
    ) -> None:
        super().__init__(parent, controller, heading)

        self.parent = parent

        self.controller = controller
        self.emitter = controller.get_emitter()

        # TODO: descriptive text here explaining how this area works
        self.custom_hbox = FolderHBox(offline.custom_button)
        self.custom_hbox.get_button().connect("clicked", self._on_custom_button_clicked)

        self.pack(self.custom_hbox)

        self.emitter.connect("custom_mods_loaded", self._on_custom_mods_loaded)

    def hide_tree(self) -> None:
        # TODO: no mods message is different from collision message
        self.set_error(offline.no_mods)
        self.custom_hbox.hide_label()
        self.tree_vbox.hide()

    def present_tree(self, folder: str, store: "FastInsertListStore") -> None:
        self.custom_hbox.set_label(folder)
        self.tree.set_model(store)
        self.tree_vbox.show()
        self.hide_errors()

    def _on_custom_mods_loaded(
        self,
        emitter: "Emitter",
        store: "FastInsertListStore",
        folder: str,
        has_duplicates: bool,
    ) -> None:
        if len(store) == 0:
            self.hide_tree()
        else:
            self.present_tree()

        if has_duplicates:
            # TODO: block button access
            # TODO: update error message
            # cf hide_tree
            pass

    def _on_custom_button_clicked(self, button: Gtk.Button) -> None:
        local_mods = self.get_mods()
        self.parent.offline_man.get_custom_mods(local_mods)

class MissionFrame(HeadingFrame):
    def __init__(self, parent: OfflineLoader, controller: "Controller") -> None:
        super().__init__(heading=offline.mission_frame)

        self.parent = parent
        self.controller = controller
        self.emitter = controller.get_emitter()

        self.mission_hbox = FolderHBox(offline.mission_button)
        self.mission_button = self.mission_hbox.get_button()
        self.mission_button.connect("clicked", self._on_mission_button_clicked)

        self.warning = Gtk.Label(halign=Gtk.Align.START, margin_start=10, margin_bottom=5)
        self.vbox = VBox()
        self.vbox.extend([self.mission_hbox, self.warning])
        self.frame.add(self.vbox)

        self.emitter.connect("custom_mission_loaded", self._on_mission_loaded)

    def _on_mission_loaded(self, emitter: "Emitter", folder: str, is_valid: bool) -> None:
        self.mission_hbox.set_label(folder)
        if not is_valid:
            self.warning.show()
            self.warning.set_label(offline.no_mission)
        else:
            self.warning.hide()

    def _on_mission_button_clicked(self, button: Gtk.Button) -> None:
        self.parent.offline_man.get_mission()


class RadioFrame(HeadingFrame):
    def __init__(self, controller: "Controller") -> None:
        super().__init__(heading=offline.version)

        self.controller = controller

        self.id_map = {APPNAME_DAYZ: APPID_DAYZ, APPNAME_DAYZ_EXP_HUMAN: APPID_DAYZ_EXP}
        self.appid = APPID_DAYZ

        self.dayz = Gtk.RadioButton.new_with_label(None, APPNAME_DAYZ)
        self.dayz_exp = Gtk.RadioButton.new_with_label_from_widget(
            self.dayz, APPNAME_DAYZ_EXP_HUMAN
        )

        self.radio_box = HBox()
        self.radio_box.extend([self.dayz, self.dayz_exp])
        self.radio_box.set_margin_start(10)
        self.radio_box.set_margin_bottom(5)

        self.frame.add(self.radio_box)

        # TODO: abstract out of here
        default_steam_path = self.controller.query_config(Preferences.DEFAULT)
        steam_path = Path(default_steam_path)
        dayz_exp = PeFile.get_pretty_version(steam_path, APPID_DAYZ_EXP)

        self.dayz.connect("toggled", self._on_radio_toggled)
        if dayz_exp is None:
            self.dayz_exp.set_sensitive(False)

    def _on_radio_toggled(self, radio: Gtk.RadioButton) -> None:
        for el in self.dayz, self.dayz_exp:
            if el.get_active():
                label = el.get_label()
                self.appid = self.id_map[label]

    def get_appid(self) -> int:
        return self.appid


class OfflineLoader(Gtk.Box):
    def __init__(self, controller: "Controller"):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            margin_start=10,
            margin_end=10,
        )

        self.controller = controller
        self.controller.register_widget("offline_loader", self)
        self.offline_man = OfflineManager(controller)

        self.add(PageHeading(offline.heading))

        self.local_frame = ModFrame(self, controller, offline.local_frame)
        self.custom_frame = CustomModFrame(self, controller, offline.custom_frame)

        self.custom_tree = OfflineModTreeView(controller)
        self.mission_frame = MissionFrame(self, controller)
        self.radio_frame = RadioFrame(controller)

        self.scrollable = Gtk.ScrolledWindow(
            vexpand=True, propagate_natural_height=True
        )

        self.content_box = VBox(spacing=5)
        self.content_box.extend(
            [
                self.local_frame,
                self.custom_frame,
                self.mission_frame,
                self.radio_frame,
            ]
        )

        # TODO: share ConnectBox class with preconnect dialog?
        self.button_box = HBox(spacing=5)
        self.button_box.set_halign(Gtk.Align.END)
        self.button_box.set_margin_top(5)
        self.back = Gtk.Button(label="Back")
        self.ok = Gtk.Button(label="Launch", sensitive=False)
        self.back.connect("clicked", self._on_back_clicked)
        self.ok.connect("clicked", self._on_ok_clicked)
        self.connect("key-press-event", self._on_keypress)

        self.button_box.extend([self.back, self.ok])

        self.scrollable.add(self.content_box)
        self.add(self.scrollable)
        self.add(self.button_box)

    def check_button(self) -> None:
        local_mods = self.local_frame.get_mods()
        custom_mods = self.custom_frame.get_mods()
        if len(local_mods) == 0 and len(custom_mods) == 0:
            self.ok.set_sensitive(False)
        else:
            self.ok.set_sensitive(True)

    def _on_keypress(self, widget: Self, event: Gdk.EventKey) -> None:
        if event.keyval == Gdk.KEY_Escape:
            self.back.emit("clicked")

    def populate(self, store: Union["FastInsertListStore", None]) -> None:
        self.local_frame.set_model(store)
        if store is None:
            self.local_frame.start_empty()
        else:
            self.local_frame.hide_errors()
        # NOTE: suppress custom tree until explicitly loaded
        self.custom_frame.hide_all()

    def _on_back_clicked(self, button: Gtk.Button) -> None:
        self.controller.open_page(NotebookPage.MODS)

    def _on_ok_clicked(self, button: Gtk.Button) -> None:
        # appid = self.radio_frame.get_appid()
        # mission = self.mission_frame.get_mission()
        # local_mods = self.local_frame.get_mods()
        # custom_mods = self.custom_frame.get_mods()
        # cf. api.mods._hash(uid, use_custom=True)
        # TODO: dynamically calculate new symlink hashes
        # self.offline_man.setup(appid, mission, local_mods, custom_mods)
        pass
