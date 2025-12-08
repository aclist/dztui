## Dependencies:

```
pip install -r requirements.txt
```

## Setup:

1. Modify `source/conf.py`.
2. Add .rst pages to `source` tree.

## Build

```
$ mkdir build
$ sphinx-build -M html source build -a
```

## Publish
Export contents of `build/html` to host.

N.B. For GitHub, touch `.nojekyll` file on the root of the branch.
