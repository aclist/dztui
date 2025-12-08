import re

def redact(text: str) -> str:
    r = r"(/home/)([^/])*"
    cleaned = re.sub(r, r"/home/REDACTED", text)
    return cleaned
