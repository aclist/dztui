# TODO: link to here from sphinx docs

# Fetching submodules
git submodule update --recursive --init

# Installing dev dependencies
uv pip install -e .[dev]

# Building documentation
sphinx-build -M html source build -a

# Building installer package
TBD
