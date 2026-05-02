import json
from pathlib import Path
from typing import Any

def read_json(path: Path) -> Any:
    try:
        with open(path, "r") as infile:
            try:
                data = json.load(infile)
                return data
            except json.decoder.JSONDecodeError as e:
                raise e
    except OSError as e:
        raise e


def write_json(data: dict, path: Path) -> None:
    try:
        j = json.dumps(data, indent=2)
        path.write_text(j)
    except Exception as e:
        raise e
