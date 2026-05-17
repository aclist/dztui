# TODO: link to here from sphinx docs

# Setting up precommit hooks
pre-commit install

# Fetching submodules
git submodule update --recursive --init

# Installing dev dependencies
uv pip install -e .[dev]

# Building documentation
sphinx-build -M html source build -a

# Building standalone DZGUI release binaries
1. Run `./scripts/dl_pyapp.sh`
2. Run `python3 scripts/release.py`
3. Generate a release and tag against the bundled `dzgui` executable
