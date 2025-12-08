Setup
=========

DayZ license
-----------------

Prepare a Steam account with a DayZ license (i.e., own the game). From Steam's right-click menu for the game options, under ``Compatibility``, enable a Proton version ≥ ``6.8`` (or use Proton 
Experimental for the latest version).

As of this writing, any recent version of Proton should work, and it is encouraged to use the most recent one.


API keys
-------------

You will need at a minimum a :ref:`Steam Web API key<steam_api>` in order to browse the server index.

.. _steam_api:

Steam Web API key
^^^^^^^^^^^^^^^^^^

**This step is required**.

Register for a `Steam Web API key <https://steamcommunity.com/dev/apikey>`_ (free) using your Steam account. You will be asked for a unique URL for your app when registering.

Since this key is for a personal use application and does not actually call back anywhere, set a generic local identifier here like "127.0.0.1" or some other name that is meaningful to you.

Once configured, you can insert this key in the app when launching it for the first time.

.. note::
    If you are confused about this requirement, please refer to DZGUI Knowledge Base article :ref:`DZG-007<DZG-007>` for additional information.

Battlemetrics API key
^^^^^^^^^^^^^^^^^^^^^^
**This step is optional, but recommended**. Using this key lets you also connect to and query servers by their shorthand ID instead of by IP.

Register for an API key at `BattleMetrics <https://www.battlemetrics.com/account/register?after=%2Fdevelopers>`_ (free).

From the ``Personal Access Tokens area``, select ``New Token``.

Give the token any name in the field at the top.

Leave **all options unchecked** and scroll to the bottom. Select ``Create Token``.

Once configured, you can insert this key in the app when launching it for the first time (optional), or later on when using the connect/query by ID methods in the app.

.. tip::
    Each server has a unique ID. This is the string of numbers at the end of the URL. For example, in the URL ``https://www.battlemetrics.com/servers/dayz/8039514``, the ID is ``8039514``.

Next steps
--------------
Proceed to the next section for usage instructions.
