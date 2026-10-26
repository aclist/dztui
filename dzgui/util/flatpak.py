import logging
import subprocess

from dzgui.const.constants import APP_NAME, FLATPAK_APPID, GTK_APP_ID, TMP_PATH

logger = logging.getLogger(APP_NAME)


def apply_overrides(xdg: dict[str, str]) -> None:
    try:
        # NOTE: D-Bus registration required for sandbox
        args = [
            "flatpak",
            "--user",
            "override",
            f"--own-name={GTK_APP_ID}",
            FLATPAK_APPID,
        ]
        subprocess.run([*args], capture_output=True)

        paths: list[str] = []
        paths.extend([*xdg.values()])
        paths.append(TMP_PATH)

        for path in paths:
            args = [
                "flatpak",
                "--user",
                "override",
                f"--filesystem={path}",
                FLATPAK_APPID,
            ]
            subprocess.run([*args], capture_output=True)
    except Exception as e:
        logger.critical(e)
