import json
import shlex
from pathlib import Path


"""
Convert legacy dztuirc to config.json
"""


class UnsupportedKey(Exception):
    pass


def str2bool(string: str) -> bool:
    s = string.lower()
    match s:
        case "":
            return False
        case "0":
            return False
        case "1" | "2":
            return True
        case "false":
            return False
        case "true":
            return True
        case _:
            raise UnsupportedKey(f"The key {s} is not a valid config key.")


def rc2json(file: Path) -> str:
    with open(file, "r") as f:
        lex = shlex.shlex(f.read())
        lex.whitespace += "="

    keys = {}
    ips: list[str] = []

    toggles = ["auto_install", "fullscreen"]
    deprecated = ["staging_dir", "src_path", "steam_path", "debug", "branch"]

    while True:
        tok = lex.get_token()
        ntok = lex.get_token()

        if ntok is not None:
            ntok = ntok.strip('""')

        if tok in deprecated:
            continue
        elif tok in toggles:
            ntok = str2bool(ntok)
        elif tok == "preferred_client":
            tok = "client"
        elif tok == "api_key":
            tok = "bm_api"
        elif tok == "ip_list":
            while True:
                ntok = lex.get_token().strip('""')
                if ntok == ")":
                    break
                # TODO: make test for this
                # NOTE: strip malformed records from ancient config file versions
                if len(ntok.split(":")) == 3 and ntok.split(":")[2] != "":
                    ips.append(ntok)
            continue

        if not tok:
            break

        keys[tok] = ntok

    keys["ip_list"] = ips
    keys["use_miles"] = False
    keys["start_tab"] = 0
    return json.dumps(keys, indent=2)
