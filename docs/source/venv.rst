After satisfying the dependencies above, create a virtual environment (venv) and install PyGObject:

If you have ``uv`` as your Python version manager, invoke the following:

.. code:: console

    uv venv --python 3.13 $HOME/.virtualenvs/dzgui
    source $HOME/.virtualenvs/dzgui/bin/activate
    uv pip install PyGObject

If you installed the ``python3.13`` package directly instead of ``uv``, use the below:

.. code:: console

   python3.13 -m venv $HOME/.virtualenvs/dzgui
   source $HOME/.virtualenvs/dzgui/bin/activate
   pip install PyGObject

You can now proceed to the :ref:`Installscript`.
After installation, refer to the additional remarks below.

.. important::
   Since PyGObject is localized to a venv, it is advisable to create a wrapper script to ensure
   the venv is activated on subsequent invocations of DZGUI.

.. code:: console

    #!/usr/bin/env bash
    source $HOME/.virtualenvs/dzgui/bin/activate
    <insert your path to dzgui.sh>

Make sure to update the placeholder path on the last line. For example, if you ran the
installscript from your home directory, the wrapper script would look like:

.. code:: console

    #!/usr/bin/env bash
    source $HOME/.virtualenvs/dzgui/bin/activate
    $HOME/dzgui.sh

Save this wrapper script in a location of your choice, e.g., ``mywrapper.sh`` and set the
executable bit: ``chmod +x mywrapper.sh`` This script will be your entrypoint for
future invocations of DZGUI, so you should launch it, not ``dzgui.sh``
