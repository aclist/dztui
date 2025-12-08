Knowledge Base
==================

.. _DZG-001:

DZG-001: Periodically getting dropped from servers, or servers appear unreachable
------------------------------------------------------------------------------------
It is a longstanding issue in DayZ that the game opens a large number of connections when querying servers and/or while connected to servers.
This can result in excess traffic on the user's PC which, depending on how much headroom your network has, can lead to getting dropped, unresponsiveness, or a timeout.

If you are on Wi-Fi, try switching to a wired connection and see if the problem resolves itself. If it does, your wireless router settings do not have enough headroom for max simultaneous connections. Use a wired connection, or update your network settings to a more permissive setup.

Bohemia has acknowledged this issue going back 10+ years and stated that DayZ has a heavy impact on the network, but there is as yet no proposed solution on the DayZ side.

This issue is frequently seen on Steam Deck, due to the tendency for users to use it in an untethered Wi-Fi setup.

.. _DZG-002:

DZG-002: Some servers appear locked in the official DayZ client, and are unreachable in DZGUI
-----------------------------------------------------------------------------------------------
This is a variant of :ref:`DZG-001`.

.. _DZG-003:

DZG-003: On Steam Deck, DayZ becomes unresponsive/sluggish over time
---------------------------------------------------------------------------------------------
When DayZ is open for 1+ hours, a gradual loss in performance and FPS may occur on the Steam Deck.

A solution that seems to work for most users is to install `Cryo Utilities <https://github.com/CryoByte33/steam-deck-utilities>`_, a third-party performance management application.

.. _DZG-004:

DZG-004: On Steam Deck, some mods in the Workshop show a black screen when DZGUI attempts to open them
---------------------------------------------------------------------------------------------------------
This is a bug in the Steam client that is being tracked at Valve's Steam for Linux issue tracker here: https://github.com/ValveSoftware/steam-for-linux/issues/9598.

To resolve this issue, manually intervene in the Steam client by selecting a different context (e.g., Store, Library), waiting for it to load, then navigating back to the Workshop context. This should 
clear the blockage and allow the contents to render.

.. _DZG-005:

DZG-005: Rendering problems with objects in the Winter Chernarus v2 mod
--------------------------------------------------------------------------

This mod has LOD (level of detail) bugs that may cause objects near the player, such as leaves, to render incorrectly, or cause distant trees to pop in abruptly. This is an acknowledged issue with the mod itself, not with DayZ or DZGUI.

There is no user-side fix for this issue; it is a problem solely on the mod side.

.. _DZG-006:

DZG-006: After moving DayZ to another drive, DZGUI fails to locate it on initial setup
----------------------------------------------------------------------------------------
If you recently moved the location of DayZ using Steam's internal dialogs, it may take some time for this information to update internally on Steam's side.

Steam stores the location of installed games in a unified file, and DZGUI checks this file during initial setup to determine where Steam claims DayZ is installed.

If you recently moved DayZ to a different drive or partition but did not restart Steam, this information may be out of date, causing Steam to report the wrong location.

Try restarting the Steam client and starting the DZGUI initial setup again.

.. _DZG-007:

DZG-007: Why do I need a Steam Web API key? Is it safe?
----------------------------------------------------------
In order to provide a server browser showing a searchable list of all available servers, DZGUI utilizes the Steam Web API.

Actual connections and queries to individual servers are performed directly between the computer and the DayZ server.

DZGUI gets its server information directly from the most authoritative source: Steam. It does this by letting the user be solely in control of their own API key and the application in an authenticated way. Users explicitly get permission to use a Web API key instead of scraping DayZ server info from third-party sites.

Everything that happens between DZGUI and the Steam Web API endpoint takes place solely on the user's computer, using a GET request (fetch server list), and no information gets sent back to the developer. DZGUI does not scrape third party DayZ APIs without permission.

There is some misconception that a Steam Web API key could be used to gain information about a user's account or control their account. Not only is this not possible, but the Web API key is used solely by the user on their own computer and is protected by Steam Guard.

A Steam Web API key is the most strict way of getting authentic, reliable, and consistent server information in a zero-trust model.

You are responsible for the creation, storage, management, and revocation of your Web API key.
