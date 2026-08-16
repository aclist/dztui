Knowledge Base
==================

.. _DZG-001:

DZG-001: Timeouts occur while trying to query a specific server
------------------------------------------------------------------------------------
The leading cause of specific servers periodically timing out is local network configuration.

Many third-party DayZ servers use a server rental/hosting provider with DDoS protection.
This can cause responses from servers to originate from a server other than the one originally queried.

Consumer-grade routers are likely to drop this traffic as invalid due to how they handle NAT (network address translation).
By contrast, wireless routers and enterprise-grade routers may be less likely to have this issue.

If you find that a specific server is unresponsive for you when it shouldn't be, add a port forwarding rule to your router's settings for
the server's query port.

In addition, packets sent from server responses are expected to be a standard size (see warning below).
Deviation from this may cause your router to discard incoming responses from the server.


.. important::
   Ensure that MTU (maximum tranmission unit) on your network is set to the standard size of 1,500 bytes.
   If your network preferences or router have "jumbo" frames enabled, packets may be dropped, causing server queries to time out.

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

DZG-008: Periodically getting dropped from servers while connected
-------------------------------------------------------------------
In some cases, DayZ opens a large number of connections while connected to servers.

If your network does not have enough headroom or has settings departing from defaults, this may lead to getting dropped from servers,
unresponsiveness, or a timeout.

If you are on Wi-Fi, try switching to a wired connection and see if the problem resolves itself. Consumer Wi-Fi routers
tend to have less headroom for simultaneous connections than their wired counterparts.

DZG-009: Floating dialogs appear maximized on tiling window managers
-------------------------------------------------------------------

The main DZGUI window and its child dialogs are expected to be rendered as floating by your window manager.
DZGUI sends window manager hints to this effect, but tiling window managers designed to bisect the screen into quadrants (e.g., i3 window manager)
may try to always launch applications in fullscreen.

To resolve this, set specific exclusions or window hints in your WM's configuration file.
For example, for i3, add the following to your `XDG_CONFIG_HOME/i3/config` file (defaults to `$HOME/.config/i3/config`):

.. code:: console

    for_window [instance="DZGUI"] floating enable, move position center
    for_window [instance="DZGUI - Dialog"] floating enable, move position center
