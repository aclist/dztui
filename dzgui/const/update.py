"""
This file is intended to be patched by package maintainers
repackaging DZGUI for use in different distributions.

If DZGUI is going to be installed globally via a package manager
or other means and will reside in an immutable location, or needs to be
explicitly bound to a certain version, set the flag below to False.

This will disable the ability for the application to self-manage and
will suppress the "Updates available" button in the gutter.
"""

ALLOW_UPDATES = True
