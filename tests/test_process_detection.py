import unittest
from unittest.mock import patch

from dzgui.const.constants import (
    FLATPAK_APPID,
    FLATPAK_RUN_CMD,
    FLATPAK_SANDBOX,
    STEAM_CMD,
)
from dzgui.init import proc


class TestSteamDetection(unittest.TestCase):
    def test_flatpak_detection_with_multiple_running_apps(self):
        def flatpak_output(args, *, text):
            # Default `flatpak ps` includes instance, PID, app and runtime columns.
            if args == ["flatpak", "ps", "--columns=application"]:
                return f"com.spotify.Client\n{FLATPAK_APPID}\n{FLATPAK_APPID}\n"
            return f"3904921611\t1257689\t{FLATPAK_APPID}\torg.freedesktop.Platform\n"

        with (
            patch.object(proc, "has_cmd", return_value=True),
            patch.object(proc.subprocess, "check_output", side_effect=flatpak_output),
        ):
            for client in (FLATPAK_RUN_CMD, FLATPAK_SANDBOX):
                with self.subTest(client=client):
                    self.assertTrue(proc.is_steam_running(client))

    def test_flatpak_not_running(self):
        with patch.object(proc, "has_cmd", return_value=True):
            for output in ("", "com.spotify.Client\n", f"{FLATPAK_APPID}Helper\n"):
                with (
                    self.subTest(output=output),
                    patch.object(proc.subprocess, "check_output", return_value=output),
                ):
                    self.assertFalse(proc.is_flatpak_steam_running())

    def test_flatpak_not_installed(self):
        with (
            patch.object(proc, "has_cmd", return_value=False),
            patch.object(proc.subprocess, "check_output") as check_output,
        ):
            self.assertFalse(proc.is_flatpak_steam_running())
            check_output.assert_not_called()

    def test_native_steam(self):
        with patch.object(proc, "has_cmd", return_value=True):
            for running in (True, False):
                with (
                    self.subTest(running=running),
                    patch.object(proc, "is_running", return_value=running),
                ):
                    self.assertEqual(proc.is_steam_running(STEAM_CMD), running)

    def test_native_steam_while_flatpak_is_running(self):
        with patch.object(proc, "is_flatpak_steam_running", return_value=True):
            self.assertEqual(proc.is_steam_running(STEAM_CMD), False)

    def test_invalid_client(self):
        with self.assertRaises(TypeError):
            proc.is_steam_running("invalid-client")
