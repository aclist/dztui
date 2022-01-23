# DZTUI

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
|staging_dir|the intermediate path to stage downloaded mods to before moving them to the real user's `workshop_dir`. `/tmp` is used by default (see explanation below). 

### Some explanation of how steamcmd works follows:

`steamcmd` is chiefly designed for updating content on game servers. As such, it is shipped as a command-line application and is designed to be run by a user isolated from the rest of the system. It allows for programmatic login to a Steam account and fetching/updating content in a headless fashion. While this can be done anonymously for downloading game server content, to download mods tied to an actual game, you need the game license (i.e. own the game). This means you must log in to retrieve mods.

Valve recommends creating an isolated user called `steam` that is used to invoke `steamcmd` and fetch content. This is a reasonable suggestion and makes sense for a server context in particular. Once logged in, `steamcmd` by design stores and hashes the login credentials to uniquely identify the user and obviate further manual password entry from the same account. After prompting for a password (and 2FA code, where applicable), it won't ask for them again unless the hash is removed or the login user is changed.

You must create the `steam` user (or some other user of your choice) on the local system, and install `steamcmd` from your repositories or download the upstream binary.

For our purposes, isolating the user still seems like a good idea, but this introduces a challenge: how to fetch the content as the user `steam` and then make it available to the real user in the least kludgy manner possible? Obviously, if the users are isolated from each other, the `steam` user shouldn't be allowed to wantonly write files to the real user's space, and vice versa, the real user shouldn't be able to go into the `steam` user's space.

I initially thought making use of a common/shared directory that both users have group permissions to would be good: the `steam` user could fetch the mods, then move them to this common directory, which is set to recursively inherit permissions. The real user then grabs the content out of there and puts it in their real mod path. This seemed overengineered, though, and you have to mess about with group permissions  and umasks, and would a user create a totally clean directory for this purpose, as I did, or just set their `$HOME`? It seemed rife with problems. Another alternative here would be to use access control lists (ACL), but, again,  this just seemed like overkill, and I didn't like the idea of users wantonly moving files in and out of some unspecified directory, especially if someone chose to set this as an important directory path.

Eventually, I chose something more streamlined: 

1. We use `sudo` to perform a one-time invocation of `steamcmd` as the `steam` user (`sudo -u $steamcmd_user ...`)
2. steamcmd fetches the mods as a concatenated list in one go, and writes them to `/tmp` (`+force_install_dir $staging_dir`). `/tmp` seemed like the ideal choice because, by design, all users can see this directory, and it uses the sticky bit, so it's painless to change ownership of the incoming files to the real user and move them out. Lastly, `/tmp` is the de facto place for ephemeral files, so there is no worry about destructively changing files if the write operation is malformed for some reason--although it is unlikely to be. Note that `steamcmd` does not have great error handling or provide correct return codes even if the wrong credentials are supplied, and likes to write a `steamapps`directory (albeit empty) into the destination directory when failing. Taking this into account, `/tmp` seemed like a good place.
3. `sudo` is used to change ownership of the incoming files back to the real user and its effective group id (`sudo chown -R $USER:$gid $staging_dir/steamapps`)
4. The individual mod ID directories are copied out of `/tmp` to the real mod path.
4. Once finished, the directory leftovers are removed from `/tmp` (`rm -r $staging_dir/steamapps`). The `steamapps` root may contain some files we don't want to conflict with the real workshop path, so we just take the mods, not the whole directory stack. Later invocations of `steamcmd` may fail if there is some detritus in `steamapps`, so it needs to be removed.

There are other ways of solving this, but in terms of skipping group and user management and keeping things fast and simple, this seems reasonable. At most, the user will be asked to input their Stream credentials once and never again until the hash is revoked, and their password (sudo) once. In addition, mod downloading stops becoming a recurring need once it's been done for a few servers.

Obviously, those credentials go through `steamcmd` directly to Valve and not through this script. See the function `auto_mod_download()` to see the exact command being used.

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
- Official servers do not get indexed by server trackers in the usual manner, so this works only with custom servers. It might be possible to include a manifest of official servers in a future revision, however.
- ~~In testing, at least one server behaved strangely despite the correct launch parameters being given and refused to start. (Investigating)~~ **Thanks to the user scandalouss for help in resolving this issue**
- You may still encounter weird bugs from DayZ itself due to the unstable nature of the client. (E.g., "User is not connected to Steam" when loading into a map.)
- Wasn't tested on esoteric terminal emulators or fancy configs. (Tested against urxvt)

## Q&A

Q. Why not use a custom server query API?

A. It is technically feasible using A2S, but is complicated and offers little benefit other than further automation (no API registration) and slightly more granular control over the server info returned. Still, I would like to include that at some point through a helper file.

Q. Why not allow browsing all servers in real time?

A. It greatly complicates the scope. There are 10K+ servers that would have to be queried and some kind of manifest created, to say nothing of sorting, searching, pagination, etc. Having a simple heads-up list of your servers of interest should suffice for most use cases. I am thinking of rewriting this in curses as a fully-featured browser at some point, but we would have to see what improvements are made to the in-game browser and launcher to see if this is maintainable or even necessary in the first place.

Q. What about adding the field «insert some field name here»?

A. See above. "Number of players in queue" could be added to help decide whether to join a full server, but this requires a custom API.



