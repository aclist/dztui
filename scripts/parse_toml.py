import tomllib
from pathlib import Path

root = Path(__file__).resolve().parents[1]

def get_entrypoint() -> None:
    p = root.joinpath("pyproject.toml")
    with open(p, "rb") as f:
        t = tomllib.load(f)

    name = t["project"]["name"]
    return t["project"]["scripts"][name]
