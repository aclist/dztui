from typing import Self, TYPE_CHECKING

from dzgui.strings import offline
from dzgui.util import css
from dzgui.views.components.frame import HeadingFrame
from dzgui.views.trees.tree_mods import ModTreeView


import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa

if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller

# FIXME: grab focus of outer page
# TODO: if any custom mods, symlink them before connecting proceeding


class OfflineLoader(Gtk.Box):
    def __init__(self, controller: "Controller"):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            margin_start=10,
            margin_end=10,
        )

        # TODO: wrap entire page in scrollable
        self.controller = controller
        self.controller.register_widget("offline_loader", self)

        label = Gtk.Label(label=offline.heading)
        label.set_halign(Gtk.Align.CENTER)
        css.add_class(label, "page-heading")
        self.add(label)

        # TODO: wrap trees in scrollable
        # TODO: suppress trees if there are no mods
        self.local_mods = ModTreeView(controller)
        self.scr = Gtk.ScrolledWindow()
        self.scr.add(self.local_mods)
        self.scr.set_size_request(600, 400)
        # TODO: strings
        self.local_frame = HeadingFrame(self.scr, "Installed mods")

        # TODO: update selected count statusbar when changed
        sel = self.local_mods.get_selection()
        sel.connect("changed", self._on_selection_changed)

        # TODO: abstract into class
        # TODO: folder label
        # TODO: descriptive text here explaining how this area works
        # TODO: use statusbar msg from format.format_mods
        # TODO: strings
        self.custom_button = Gtk.Button(
            label="Set custom mod folder", halign=Gtk.Align.START
        )
        self.custom_button.connect("clicked", self._on_custom_button_clicked)
        self.custom_mods = Gtk.TreeView()
        self.custom_mods_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, margin_start=10, margin_bottom=10
        )
        self.custom_mods_box.add(self.custom_button)
        self.custom_mods_box.add(self.custom_mods)

        # TODO: strings
        self.custom_frame = HeadingFrame(self.custom_mods_box, "Custom mods")

        self.mission_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, margin_start=10, margin_bottom=10
        )
        # TODO: strings
        self.mission_button = Gtk.Button(label="Select mission folder")
        self.mission_label = Gtk.Label()

        self.mission_box.add(self.mission_button)
        self.mission_box.add(self.mission_label)

        # TODO: strings
        self.mission_frame = HeadingFrame(self.mission_box, "Mission")

        self.radio_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, margin_start=10, margin_bottom=10
        )
        # TODO: strings
        # TODO: disable if not available, use PeFile
        self.dayz = Gtk.RadioButton.new_with_label(None, "DayZ")
        self.dayz_exp = Gtk.RadioButton.new_with_label_from_widget(
            self.dayz, "DayZ Experimental"
        )
        self.radio_box.add(self.dayz)
        self.radio_box.add(self.dayz_exp)
        self.radio_frame = HeadingFrame(self.radio_box, "DayZ Version")

        self.scrollable = Gtk.ScrolledWindow(
            vexpand=True, propagate_natural_height=True
        )
        # TODO: use same button anchoring logic as preconnect dialog
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.box.add(self.local_frame)
        self.box.add(self.custom_frame)
        self.box.add(self.mission_frame)
        self.box.add(self.radio_frame)
        self.scrollable.add(self.box)

        self.add(self.scrollable)

        # TODO: use ModelFactory
        self.custom_mods = Gtk.TreeView()

        # TODO: shared ConnectBox class
        self.back = Gtk.Button()
        self.ok = Gtk.Button()
        self.back.connect("clicked", self._on_back_clicked)
        self.ok.connect("clicked", self._on_ok_clicked)
        self.connect("key-press-event", self._on_keypress)

    def _on_keypress(self, widget: Self, event: Gdk.EventKey) -> None:
        if event.keyval == Gdk.KEY_Escape:
            self.back.emit("clicked")

    def _on_selection_changed(self, sel: Gtk.TreeSelection) -> None:
        model, rows = sel.get_selected_rows()
        # TODO: update sub-statusbar with selected mods
        print(len(rows))

    def populate(self, mods: Gtk.TreeModel | None) -> None:
        self.local_mods.set_model(mods)
        # TODO: push existing model
        # TODO: set sensitivity of radio buttons
        pass

    def _on_custom_button_clicked(self, button: Gtk.Button) -> None:
        # TODO: recycle this for both buttons
        folder = self.controller.set_custom_folder()
        if folder is not None:
            # TODO: parse mods from here
            # TODO: offline mod manager would be cleaner
            print(folder)

    def _on_back_clicked(self, button: Gtk.Button) -> None:
        from dzgui.const.enum import NotebookPage

        self.controller.open_page(NotebookPage.SERVERS)

    def _on_ok_clicked(self, button: Gtk.Button) -> None:
        pass
        """
        create symlinks if there are custom mods
        cf. rebuild_symlinks()
        """
