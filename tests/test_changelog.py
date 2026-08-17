import re
import pytest

from pathlib import Path


@pytest.fixture
def changelog(request) -> None:
    root = request.config.rootpath
    changelog = Path(root).joinpath("CHANGELOG.md").read_text()
    return changelog


def count_hash(line: str) -> int:
    cnt = 0
    for c in line:
        if c == "#":
            cnt += 1
    return cnt


@pytest.mark.FOO
def test_changelog_prefix(changelog) -> None:
    r = r".*(\[.*\]).*"
    lines = changelog.splitlines()
    sort = sorted(lines)
    match = [line for line in sort if line.startswith("#")]
    for m in match:
        if "Changelog" in m:
            assert count_hash(m) == 1
        elif re.match(r, m) is not None:
            assert count_hash(m) == 2
        else:
            assert count_hash(m) == 3
