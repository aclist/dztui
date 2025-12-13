import re

def redact(text: str) -> str:
    r = r"(/home/)([^/])*"
    cleaned = re.sub(r, r"/home/REDACTED", text)
    return cleaned

def redact_log(record: list) -> list[str]:
    """
    requests library includes Steam API key in URL params
    """
    clean = []
    for item in record:
        if "&key=" in item:
            pat = r"(.*&key=)(\S+)(.*)"
            scrubbed = re.sub(pat, r"\1REDACTED\3", item)
            clean.append(scrubbed)
        else:
            clean.append(item)
    return clean
