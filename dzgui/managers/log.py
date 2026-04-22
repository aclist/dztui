import logging
from pathlib import Path
from dzgui.util.strings import delimiter

logger = logging.getLogger(__name__)


class LogManager:
    def __init__(self) -> None:
        self.CRITICAL = "CRITICAL"
        self.WARNING = "WARNING"

    # TODO: more of a static method
    def get_alerts(self, log_path: Path) -> tuple[int]:
        try:
            with open(log_path, "r") as f:
                lines = f.read().splitlines()
            errors = [
                line for line in lines if line.split(delimiter)[1] == self.CRITICAL
            ]
            warnings = [
                line for line in lines if line.split(delimiter)[1] == self.WARNING
            ]
            return len(warnings), len(errors)
        except Exception as e:
            logger.critical(e)
            return 0, 0
