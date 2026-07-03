import logging
import re
from typing import Literal

api_filter = r"(.*&key=)([^&]*)(.*)"
home_filter = r"(/home/)([^/]*)(.*)"
REDACTED = r"\1REDACTED\3"
REDACTION_PATTERNS = [api_filter, home_filter]


def redact_home(text: str) -> str:
    pat = re.compile(home_filter)
    cleaned = pat.sub(REDACTED, text)
    return cleaned


class RedactionFilter(logging.Filter):
    def __init__(self, patterns: list[str] | None = None) -> None:
        super().__init__()
        self._patterns = [re.compile(pat) for pat in (patterns or [])]

    def filter(self, record: logging.LogRecord) -> Literal[True]:
        for pattern in self._patterns:
            try:
                record.msg = pattern.sub(REDACTED, record.msg)
            except TypeError:
                exception_text = f"{type(record.msg).__name__}: {record.msg}"
                record.msg = pattern.sub(REDACTED, exception_text)
        return True
