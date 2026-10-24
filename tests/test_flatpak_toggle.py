import pytest

from dzgui.const.constants import FLATPAK_RUN_CMD, FLATPAK_SANDBOX
from dzgui.const.enum import Preferences
from dzgui.views.pages.options import FlatpakToggleField


class MockController:
    def __init__(self) -> None:
        self.command: str

    def update_config(self, context: Preferences, cmd: str) -> None:
        self.command = cmd

    def get_command(self) -> str:
        return self.command


@pytest.mark.parametrize("index, expect", [(0, FLATPAK_RUN_CMD), (1, FLATPAK_SANDBOX)])
def test_toggle(index: int, expect: str) -> None:
    controller = MockController()
    toggle = FlatpakToggleField(controller)
    match index:
        case 0:
            toggle.radio2.set_active(True)
            toggle.radio1.set_active(True)
        case 1:
            toggle.radio1.set_active(True)
            toggle.radio2.set_active(True)
    assert controller.get_command() == expect
