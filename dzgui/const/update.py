"""
This file is intended to be patched by package maintainers
repackaging DZGUI for use in different distributions.

If DZGUI is going to be installed globally via a package manager
or other means and will reside in an immutable location, or needs to be
explicitly bound to a certain version, set the flag below to False.

This will disable the following:

- Version update checks at startup
- Ability to toggle between Stable/Testing branches in the Options menu
"""

ALLOW_UPDATES = True
