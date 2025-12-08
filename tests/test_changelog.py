def test_headings():
    with open("CHANGELOG.md", "r") as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith("#"):
            pass
        # TODO: use regex
    pass
