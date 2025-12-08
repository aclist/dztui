Installation
==================

Dependencies
----------------------

If not already installed, the below can be found in your system’s package manager.

If any dependencies are missing when the application starts, it will warn you, so you need not take any preemptive measures here.

- curl
- jq
- PyGObject (python-gobject)
- steam
- wmctrl or xdotool
- zenity

.. note::
    All dependencies are installed out of the box on Steam Deck.

Downloading
------------------

Automatic installation
^^^^^^^^^^^^^^^^^^^^^^^
Invoke the command below from a terminal:

.. code:: console

    curl -s "https://codeberg.org/aclist/dztui/raw/branch/dzgui/install.sh" | bash


Manual installation
^^^^^^^^^^^^^^^^^^^^

Clone the repository:

.. code:: console

    git clone https://codeberg.org/aclist/dztui.git

Set the executable bit on ``dzgui.sh``:

.. code:: console

    chmod +x dzgui.sh


Launch the script:

.. code:: console

    ./dzgui.sh

nixOS installation
^^^^^^^^^^^^^^^^^^^
Two packages are independently maintained by other contributors. Each takes a slightly different approach:

- https://github.com/lelgenio/dzgui-nix
- https://github.com/jiriks74/dzgui.flake

Next steps
---------------
Proceed to the next section for setup instructions.
