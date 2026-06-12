from __future__ import annotations
from enum import Enum
from typing import Self, Sequence, TYPE_CHECKING, Union

from dzgui.util import css
from dzgui.const.constants import (
    APPID_DAYZ,
    APPID_DAYZ_EXP,
    APPNAME_DAYZ,
    APPNAME_DAYZ_EXP_HUMAN,
    EDIT_DELETE,
    ERROR,
    FOLDER,
)
from dzgui.const.enum import NotebookPage
from dzgui.managers.offline import OfflineManager
from dzgui.strings import generic, offline
from dzgui.views.components.buttons import Icon, IconTextButton
from dzgui.views.components.eventbox import InfoEventBox
from dzgui.views.components.frame import HeadingFrame
from dzgui.views.components.scrollable import NoOverlayScrolledWindow
from dzgui.views.trees.tree_mods import OfflineModTreeView


import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GObject  # noqa

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller
    from dzgui.controllers.emitter import Emitter
    from dzgui.model.model_factory import FastInsertListStore


class FolderError(Enum):
    NO_VALID_MODS = 1
    NO_VALID_MISSION = 2


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


class ErrorPopover(Gtk.Popover):
    def __init__(self) -> None:
        super().__init__(position=Gtk.PositionType.RIGHT)

        self.hbox = HBox()
        self.label = Gtk.Label(label="", margin_start=10, margin_end=10)
        error_icon = Icon(ERROR, margin_start=10)
        self.hbox.extend([error_icon, self.label])
        self.add(self.hbox)
        self.show_all()
        self.popdown()

    def set_label(self, error: FolderError, msg: str) -> None:
        match error:
            case FolderError.NO_VALID_MODS:
                prefix = offline.no_mods
            case FolderError.NO_VALID_MISSION:
                prefix = offline.no_mission
        self.label.set_label(f"{prefix}: '{msg}'")


class FolderHBox(HBox):
    def __init__(self, controller: "Controller", btn_label: str, eb_text: str) -> None:
        super().__init__(spacing=10)

        self.set_margin_start(5)
        self.set_margin_end(10)
        self.set_margin_bottom(5)

        self.folder = ""
        self.controller = controller
        self.emitter = controller.get_emitter()

        self.eb = InfoEventBox(eb_text, controller)
        self.button = IconTextButton(FOLDER, btn_label, Gtk.PositionType.LEFT)
        self.button.set_halign(Gtk.Align.START)
        self.button.set_image_position(Gtk.PositionType.LEFT)

        self.scrolled_label = Gtk.ScrolledWindow(
            propagate_natural_width=True, halign=Gtk.Align.START
        )
        self.label = Gtk.Label()
        self.scrolled_label.add(self.label)

        self.unset_button = IconTextButton(EDIT_DELETE, offline.unset_button)
        self.unset_button.connect("clicked", self._on_unset_clicked)

        self.spinner = Gtk.Spinner()
        self.extend(
            [self.eb, self.button, self.spinner, self.scrolled_label, self.unset_button]
        )

        self.pop = ErrorPopover()
        self.pop.set_relative_to(self.button)

        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)

    def start_spinner(self) -> None:
        self.spinner.show()
        self.spinner.start()

    def stop_spinner(self) -> None:
        self.spinner.hide()
        self.spinner.stop()

    def _on_unmap(self, widget: Self) -> None:
        self.unset_button.hide()
        self.label.set_label("")
        self.scrolled_label.hide()

    def _on_map(self, widget: Self) -> None:
        self.spinner.hide()
        self.scrolled_label.show()
        self.unset_button.hide()

    def _on_unset_clicked(self, button: Gtk.Button) -> None:
        self.label.set_label("")
        self.unset_button.hide()
        # FIXME: rename signal
        self.emitter.emit("custom_mods_unloaded", self)

    def get_button(self) -> Gtk.Button:
        return self.button

    def hide_label(self) -> None:
        self.label.hide()

    def get_folder(self) -> str:
        return self.folder

    def set_folder(self, folder: str) -> None:
        prefix = offline.folder_prefix
        self.folder = folder
        self.label.set_markup(prefix + folder)
        self.label.show()
        self.unset_button.show()

    def present_error(self, error: FolderError, msg: str) -> None:
        self.unset_button.hide()
        self.pop.set_label(error, msg)
        self.pop.popup()


class ModFrame(HeadingFrame):
    def __init__(
        self, parent: OfflineLoader, controller: "Controller", label: str
    ) -> None:
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

        self.connect("unmap", self._on_unmap)

    def _on_unmap(self, widget: Self) -> None:
        self.tree.set_model(None)
        self.tree_vbox.hide()

    def start(self, store: "FastInsertListStore") -> None:
        self.tree.set_model(store)
        self.show_tree()

    def get_mods(self) -> list[str]:
        model, treeiters = self.tree.get_selection().get_selected_rows()
        if model is None:
            return []
        if type(self) is CustomModFrame:
            return [model[_iter][2] for _iter in treeiters]
        else:
            # NOTE: pre-existing, canonical symlinks to published mods
            return [model[_iter][1] for _iter in treeiters]

    def show_tree(self) -> None:
        self.tree_vbox.show()

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
        # TODO: cleaner delegation
        # simply send int value or use emitter
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

        self.custom_hbox = FolderHBox(
            controller, offline.custom_button, offline.custom_eventbox
        )
        self.custom_hbox.get_button().connect("clicked", self._on_custom_button_clicked)

        self.pack(self.custom_hbox)

        self.emitter.connect("custom_mods_loaded", self._on_custom_mods_loaded)
        self.emitter.connect("custom_mods_unloaded", self._on_custom_mods_unloaded)

        self.connect("map", self._on_map)

    def _on_map(self, widget: Self) -> None:
        self.hide_tree()

    def _on_custom_mods_unloaded(self, emitter: "Emitter", widget: FolderHBox) -> None:
        # TODO: kludgy workaround for generic button emitting global signal
        if widget == self.custom_hbox:
            self.hide_tree()

    def hide_tree(self) -> None:
        self.custom_hbox.hide_label()
        self.tree.set_model(None)
        self.tree_vbox.hide()

    def present_error(self, folder: str) -> None:
        self.hide_tree()
        self.custom_hbox.present_error(FolderError.NO_VALID_MODS, folder)

    def present_tree(self, store: "FastInsertListStore", folder: str) -> None:
        self.custom_hbox.set_folder(folder)
        self.tree.set_model(store)
        self.tree_vbox.show()

    def _on_custom_mods_loaded(
        self,
        emitter: "Emitter",
        store: "FastInsertListStore",
        folder: str,
    ) -> None:
        self.custom_hbox.stop_spinner()
        if len(store) == 0:
            self.present_error(folder)
        else:
            self.present_tree(store, folder)

    def _on_custom_button_clicked(self, button: Gtk.Button) -> None:
        callback = self.custom_hbox.start_spinner
        # TODO: cleaner delegation
        self.parent.offline_man.find_custom_mods(callback)

    def get_folder(self) -> str:
        return self.custom_hbox.get_folder()


class MissionFrame(HeadingFrame):
    def __init__(self, parent: OfflineLoader, controller: "Controller") -> None:
        super().__init__(heading=offline.mission_frame)

        self.parent = parent
        self.controller = controller
        self.emitter = controller.get_emitter()

        self.mission_hbox = FolderHBox(
            controller, offline.mission_button, offline.mission_eventbox
        )
        self.mission_button = self.mission_hbox.get_button()
        self.mission_button.connect("clicked", self._on_mission_button_clicked)

        self.frame.add(self.mission_hbox)

        self.emitter.connect("custom_mission_loaded", self._on_mission_loaded)

    def _on_mission_loaded(
        self, emitter: "Emitter", folder: str, is_valid: bool
    ) -> None:
        if is_valid:
            self.mission_hbox.set_folder(folder)
        else:
            self.mission_hbox.present_error(FolderError.NO_VALID_MISSION, folder)

    def _on_mission_button_clicked(self, button: Gtk.Button) -> None:
        self.parent.offline_man.get_mission()

    def get_mission(self) -> str:
        return self.mission_hbox.get_folder()


class RadioFrame(HeadingFrame):
    def __init__(self, parent: OfflineLoader, controller: "Controller") -> None:
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

        # TODO: cleaner delegation
        has_dayz_exp = parent.offline_man.has_dayz_exp()
        self.dayz.connect("toggled", self._on_radio_toggled)
        if has_dayz_exp is False:
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
        self.emitter = controller.get_emitter()
        self.offline_man = OfflineManager(controller)

        self.add(PageHeading(offline.heading))

        self.local_frame = ModFrame(self, controller, offline.local_frame)
        self.custom_frame = CustomModFrame(self, controller, offline.custom_frame)

        self.custom_tree = OfflineModTreeView(controller)
        self.mission_frame = MissionFrame(self, controller)
        self.radio_frame = RadioFrame(self, controller)

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
        self.button_box.set_margin_top(15)
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
        # FIXME: widget is not always in focus
        if event.keyval == Gdk.KEY_Escape:
            self.back.emit("clicked")

    def populate(self, store: Union["FastInsertListStore", None]) -> None:
        if store is None:
            return
        self.local_frame.start(store)

    def _on_back_clicked(self, button: Gtk.Button) -> None:
        self.controller.open_page(NotebookPage.MODS)

    def _on_ok_clicked(self, button: Gtk.Button) -> None:
        appid = self.radio_frame.get_appid()
        mission = self.mission_frame.get_mission()
        local_mods = self.local_frame.get_mods()
        custom_folder = self.custom_frame.get_folder()
        custom_mods = self.custom_frame.get_mods()
        self.offline_man.launch(appid, mission, local_mods, custom_folder, custom_mods)
