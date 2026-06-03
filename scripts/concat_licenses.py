from pathlib import Path

BOILERPLATE = """
This file includes the combined licenses to the following components:

1) The DZGUI utility
2) The Python interpreter
3) Third-party dependencies
    - dayzquery
    - requests
    - packaging
    - psutil
    - PyGObject
    - python-a2s

which are collectively bundled as a turnkey application and used to run the DZGUI utility.\n\n
"""
DZGUI_HEADER = "DZGUI application"
LICENSE_FILE = "LICENSE"

class CombinedLicense:
    def __init__(self) -> None:
        self.text = BOILERPLATE

    def append(self, text: str) -> None:
        self.text += text + "\n\n"

    def add_header(self, text: str) -> None:
        self.append(f"--- License for the component '{text}' follows ---")

    def add_dependency(self, dep: str) -> None:
        self.add_header(dep)

    def get_text(self) -> str:
        return self.text

def concat_license() -> str:
    combined = CombinedLicense()
    root = Path(__file__).resolve().parents[1]
    licenses = root.joinpath("licenses")

    main_license = root.joinpath(LICENSE_FILE)
    combined.add_header(DZGUI_HEADER)
    combined.append(main_license.read_text())

    for _dir in licenses.iterdir():
        # NOTE: expects a single file
        docs = _dir.glob("*")
        doc = list(docs)[0]
        combined.add_dependency(_dir.name)
        combined.append(doc.read_text())
    return combined.get_text()
