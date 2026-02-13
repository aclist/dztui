import textwrap
from typing import Self, TYPE_CHECKING

from dzgui.const.enum import Popup, Preferences
from dzgui.const.constants import NO_EXPAND, NO_FILL
from dzgui.util.open_links import open_user_workshop
from dzgui.util.strings import notice
from dzgui.views.dialogs.generic import GenericDialog
from dzgui.views.components.buttons import SteamTextButton, WebButton

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GObject, Pango  # noqa E402


if TYPE_CHECKING:
    from dzgui.controllers.mc import Controller


class WorkshopLinkDialog(GenericDialog):
    def __init__(self, controller: "Controller", text: str, button_label: str, uid: str):
        text = textwrap.dedent(text).replace("\n", " ")
        super().__init__(controller, text=notice, mtype=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK, secondary=text)
        self.controller = controller
        self.dialogBox = self.get_content_area()
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_size_request(500, 0)

        """
        If the user's ID was successfully parsed from loginusers,
        a clickable link to their workshop subscriptions is added
        """
        if uid is not None:
            button = SteamTextButton(label=button_label)
            button.set_margin_start(60)
            button.set_margin_end(60)
            button.connect("clicked", self._on_button_clicked, uid)
            self.dialogBox.pack_end(button, NO_EXPAND, NO_FILL, 0)

        self.show_all()
        self.connect("response", self._on_dialog_response)

    def _on_button_clicked(self, button: Gtk.Button, uid: str) -> None:
        # TODO: currently checks user id on instantiation
        self.controller.open_user_workshop(uid)
        #client = self.controller.query_config(Preferences.CLIENT)
        #open_user_workshop(uid, client)

    def _on_dialog_response(
        self, dialog: Self, resp: Gtk.ResponseType
    ) -> None:
        match resp:
            case Gtk.ResponseType.DELETE_EVENT:
                return
            case Gtk.ResponseType.OK:
                self.destroy()
