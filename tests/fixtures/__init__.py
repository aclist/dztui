from pathlib import Path

CWD = Path(__file__).parent
def fixture_path(fixture: str) -> str:
    return str(CWD / fixture)
