# TODO: link to here from sphinx docs

# Installing dev dependencies
uv pip install -e .[dev]

# Setting up precommit hooks
pre-commit install

# Fetching submodules
git submodule update --recursive --init

# Building documentation
sphinx-build -M html source build -a

# Building standalone DZGUI release binaries
1. Run `./scripts/dl_pyapp.sh`
# TODO: secondary script that packs this archive
2. Download cpython 3.13, linux, gnu, v3
https://github.com/astral-sh/python-build-standalone/releases/download/20251014/cpython-3.13.9%2B20251014-x86_64_v3-unknown-linux-gnu-install_only_stripped.tar.gz
3. Explicitly install dependencies into site-packages
4. Pack back into a tarball
5. Run `python3 scripts/release.py`
6. Generate a release and tag against the bundled `dzgui` executable
