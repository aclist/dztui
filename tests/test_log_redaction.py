import logging
import pytest

from dzgui.util.redact import RedactionFilter, REDACTION_PATTERNS


class RecordsListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records_list = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records_list.append(record)

    def pop(self) -> None:
        return self.records_list[-1].msg


@pytest.mark.redact
@pytest.mark.parametrize(
    "log_error, expect",
    [
        ("/home/SENSITIVE_USERNAME/subdir", "/home/REDACTED/subdir"),
        (
            "https://url.com/?api&key=SENSITIVE_KEY&results=10",
            "https://url.com/?api&key=REDACTED&results=10",
        ),
        (
            "https://url.com/?api&key=SENSITIVE_KEY",
            "https://url.com/?api&key=REDACTED",
        ),
        (
            "Error in directory: '/home/SENSITIVE_USERNAME/'",
            "Error in directory: '/home/REDACTED/'",
        ),
        (
            "Error in directory: '/home/SENSITIVE_USERNAME'",
            "Error in directory: '/home/REDACTED'",
        ),
    ],
)
def test_log_redaction(log_error: str, expect: str) -> None:
    logger = logging.getLogger("TEST")

    handler = RecordsListHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    _filter = RedactionFilter(patterns=REDACTION_PATTERNS)
    logger.addFilter(_filter)

    logger.critical(log_error)
    redacted = handler.pop()
    assert expect == redacted
