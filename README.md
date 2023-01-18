# DZTUI

**NOTE:** this project has been superseded by [DZGUI](https://github.com/aclist/dztui/tree/dzgui), which brings numerous hotfixes and quality of life features. 

Development of DZGUI is ongoing and has been driven by the needs of desktop, Steam Deck, and GUI users, and supports many more use cases and idiosyncrasies of DayZ servers. 

By comparison, the DZTUI codebase is quite ancient now and has served mainly as a proof of concept for the implementation of DZGUI. If you continue to use DZTUI in its current state, be aware that it
lacks critical features.

## What this is:

A TUI pseudo-browser for listing heads-up information on DayZ community servers, fetching and synchronizing mods, and connecting to these servers automatically without manually setting launch 
parameters.

![Alt text](example.png)

## Dependencies:

- `jq`
- `column` version with support for the `-o` flag  (part of `util-linux`)
- `steam` 

## Preparation

1. Update the sysctl `vm.max_map_count` value (see https://www.protondb.com/app/221100)
2. Enable the Steam Beta branch (Steam > Settings > Account > Beta participation)
3. Enable as your compatibility tool for the game Proton Experimental, 6.3-8, or later--or repacks based on these

## Configuration

User settings are configured at the top of the file in the "CONFIG" section. They are listed below in order of appearance in the file. This step is mandatory. Once the values have been correctly filled in, everything else should work by itself. The file comes with some default values for you for reference.

Read this carefully. The tool will prompt you if keys are configured incorrectly, but preparing your config correctly will save you time and help you understand how to modify it in the future.

Ensure that you preserve quotation marks around key values.

### Basic configuration

|Key|Meaning|
| ------ | ------ |
|steam_path|Used as a prefix to simplify interpolation of the `workshop_dir` and `game_dir` keys. If both the `workshop_dir` and `game_dir` path reside under the same install point, you need only set the key `steam_path` with the root directory of the Steam install. If you have the game installed in a path separate from the mods (multiple drives, etc.), you can safely ignore the `steam_path` variable and replace the `steam_path` prefix in the two variables below with their explicit paths.
|workshop_dir|The path to Steam workshop content (mods). Always ends in `steamapps/content/221100`.|
|game_dir|The path to the DayZ installation. Always ends in `steamapps/common/DayZ`.|
|key|Your unique API key; you must register for a free API key at https://www.battlemetrics.com/account/register?after=%2Fdevelopers|
|whitelist|A comma-separated list of server IDs you want to browse; look through https://www.battlemetrics.com/servers/dayz and select the ones you like. The server ID is the string of numbers at the end of the URL, e.g., https://www.battlemetrics.com/servers/dayz/12269772 = 12269772|
|fav|The server ID of a single server you want to flag as your "favorite" -- a default server to fast connect to when using the `f` keybinding. This value is optional and can be left blank. Note: if using a favorite server, you must include this ID in both the `whitelist` value and in the `fav` value. E.g., if `333` is your favorite server: `whitelist="111,222,333"` and `fav="333"`. Your favorite server will be listed with an arrow next to it in the table. The API enforces a sorting algorithm on requests instead of returning them in serial order, so the favorite server may not always appear in the same place in the list. |
|name|Some servers require a profile name; this can be any name of your choice. By default, it is set for you as "player". This value is optional and can be left blank.|
|separator|Used to separate fields in the table; can be a single character of your choice. This value is optional and can be left blank if you prefer simple tab justification.|
|ping|If set to 1, each of the servers is pinged once before showing the results and a time column is added; if you do not need this option, you can set it to 0 to greatly speed up load time.|
|debug|If set to 1, performs a "dry-run" connection and prints the launch parameters that would have been used instead of actually connecting to a server, provided no critical errors occur with mod setup. Doesn't quit, so can be used to perform multiple dry-runs in sequence.|

## Advanced configuration: automation with steamcmd

NOTE: This feature is experimental and is still being improved upon.

The advanced configuration is used in conjunction with the basic configuration settings above, but modifies mod downloading behavior. Note: requires installation of `steamcmd`. This is found in the "STEAMCMD Config" section of the file.

See https://developer.valvesoftware.com/wiki/SteamCMD for additional details.

|Key|Meaning|
| ------ | ------ |
|auto_install_mods|if set to 1, uses steamcmd to automatically stage mods without manual subscription necessary|
|steam_cmd_user|the name of the local system user that invokes steamcmd (recommended user is `steam`)|
|steam_username|the login handle of the real steam account that owns DayZ (this is required for mods; you cannot anonymously download mods without a license)|
|staging_dir|the intermediate path to stage downloaded mods to before moving them to the real user's `workshop_dir`. `/tmp` is used by default. This must be a writable directory. 

### Some explanation of how steamcmd works follows:

`steamcmd` is chiefly designed for updating content on game servers. As such, it is shipped as a command-line application and is designed to be run by a user isolated from the rest of the system. It allows for programmatic login to a Steam account and fetching/updating content in a headless fashion. While this can be done anonymously for downloading game server content, to download mods tied to an actual game, you need the game license (i.e. own the game). This means you must log in to retrieve mods.

Valve recommends creating an isolated user called `steam` that is used to invoke `steamcmd` and fetch content. Once logged in, `steamcmd` by design stores and hashes the login credentials to uniquely identify the user and obviate further manual password entry from the same account. After prompting for a password (and 2FA code, where applicable), it won't ask for them again until the hash expires or the login user is changed.

You must create the `steam` user (or some other user of your choice; default configuration assumes a user named `steam`) on the local system, and install `steamcmd` from your repositories or download the upstream binary.

Credentials go through `steamcmd` directly to Valve and not through this script. See the function `auto_mod_download()` to see the exact command being used.

## Usage:

Run `dztui` and it will populate the table with server info for the server IDs you selected. The column at left shows keybindings. Enter the number of a server and push Return to attempt to connect to it. The connection process checks your installed mods against the server's and will warn you if any are missing. Servers are listed in descending order of player count.

- Enter `f` to connect to your usual server (the one you marked as favorite above) without having to look through the list.
- Enter `l` to print the list of your installed mods.
- Enter `q` to quit.

Under a normal configuration, if mods are missing, links to their Workshop pages will be shown as a list, and you must open these manually and click "Subscribe" in the Steam client and wait for them to download.

If using the advanced configuration, mods will be auto-downloaded with `steamcmd` in a batch.

Once mods are finished downloading, you can attempt to reconnect. The mods will be checked for compability again and if the local and remote mod list matches, symlinks to the installed workshop content will be created in the DayZ path.

Lastly, the launch options and mod list will be concatenated and used to launch the game and connect to the destination server. The tool exits upon a successful connection attempt. Use the `debug` configuration key if you encounter problems and want to see what launch parameters would have been used. This can be useful for manual testing or seeing what mods are on certain servers. 

## Known Issues/Possible Pitfalls:

- Ubuntu's `column` package may be too old to support setting field separators correctly. (TODO: add separate section detailing how to install and compile package)
- The ping attempt is only made once as a fast check with no retries.
- It goes without saying, but you need to have a sufficiently wide enough terminal window to justify the text correctly.
- There is no pagination, so if there are more servers than lines in your terminal, you are going to have to scroll up.
- Servers don't verbosely report the version of mods they are running, so other than checking that the mod exists, we can't easily compare version differences. This means you may get booted on connect if your mod is not up to date. (Shouldn't happen due to Steam updates, but it's theoretically possible if a server is pegged to some older version). If that happens, you could manually install the desired version and reconnect.
- The server protocol enforces a maximum length of 64 characters, so server names should never exceed the acceptable width of the table, making truncation unneccessary.
- This was not tested with Flatpak steam or Steam native runtime. If there is a particular method of invocation for those, submit an issue.
- Official servers do not get indexed by server trackers in the usual manner, so this works only with custom servers. (DZGUI supports official servers)
- You may still encounter weird bugs from DayZ itself due to the unstable nature of the client. (E.g., "User is not connected to Steam" when loading into a map.)
- Wasn't tested on esoteric terminal emulators or fancy configs. (Tested against urxvt)

## Q&A

Q. Why not use a custom server query API?

A. It is technically feasible using A2S, but is complicated and offers little benefit other than further automation (no API registration) and slightly more granular control over the server info returned. Still, I would like to include that at some point through a helper file.

Q. Why not allow browsing all servers in real time?

A. This feature exists in DZGUI. It is not ideal for a TUI client due to the need for pagination/scrolling.
