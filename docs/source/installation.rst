Installation
==================

Basic runtime dependencies
---------------------------------

If not already installed, the below can be found in your system’s package manager.

If any dependencies are missing when the application starts, it will warn you, so you need not take any preemptive measures here.

- curl
- jq
- steam
- wmctrl or xdotool
- zenity

.. note::
    All dependencies are installed out of the box on Steam Deck.

UI dependencies (Python and PyGObject)
---------------------------------------
.. important::
    As of version 6.0.0, you must have a valid Python 3.13 and matching PyGObject environment.
    Depending on your distribution, this may require additional manual intervention.

Arch Linux (vanilla variants)
^^^^^^^^^^^^^^^^^^^^^^
You will need the ``python3.13`` package, if it is not already installed.

Install the following build dependencies:

.. code:: console

   sudo pacman -S cmake gcc pkgconf python-cairo

.. include:: venv.rst

CachyOS (Arch)
^^^^^^^^^^^^^^^^^^^^^^^
Refer to the build instructions for Arch Linux first.
The ``python3.13`` package is not available on CachyOS, so it is recommended to
use ``uv`` to manage Python versions.

.. code:: console

   sudo pacman -S uv

.. include:: venv.rst

Manjaro 26 (Arch)
^^^^^^^^^^^^^^^^^^^^^^^
If Python 3.13 is not already available out of the box, refer to the build instructions for :ref:`Arch Linux (vanilla variants)`.

Debian 13 variants
^^^^^^^^^^^^^^^^^^^^^^^
Python 3.13 and PyGObject are available out of the box. No additional steps are necessary.
You can proceed to the :ref:`Installscript`.

Fedora 43 variants
^^^^^^^^^^^^^^^^^^^^^^^
Fedora 43 ships with a newer version of Python (3.14), so you must set up Python 3.13 in its own
virtual environment (venv) to prevent it from conflicting with the system package.

Install the following build dependencies:

.. code:: console

    sudo dnf install cairo cairo-devel cairo-gobject-devel gcc python3.13 python3.13-devel

.. include:: venv.rst

Ubuntu 24 variants
^^^^^^^^^^^^^^^^^^^^^^
Ubuntu ships with an older version of Python (3.12). You must install additional dependencies.
Add the PPA below to add Python 3.13 to your sources:

.. code:: console

    sudo add-apt-repository ppa:deadsnakes/ppa

Install the following build dependencies:

.. code:: console

    sudo apt install python3.13 python3.13-venv python3.13-dev build-essential python3-gi-cairo pkg-config libgirepository-2.0-dev libcairo2-dev

.. include:: venv.rst

Installscript
-----------------------

Invoke the command below from a terminal. This script fetches the main DZGUI script from the repository,
makes it executable, and launches DZGUI's first-time setup. After running this installscript, you will
have the file ``dzgui.sh`` wherever you invoked the command.

.. code:: console

    curl -s "https://codeberg.org/aclist/dztui/raw/branch/dzgui/install.sh" | bash

nixOS installation
----------------------
Two packages are independently maintained by other contributors. Each takes a slightly different approach.
nixOS packages are standalone and do not require cloning the git repository.

- https://github.com/lelgenio/dzgui-nix
- https://github.com/jiriks74/dzgui.flake

Next steps
---------------
Proceed to the next section for setup instructions.
