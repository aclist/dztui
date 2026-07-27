### IntroductionPage
title_intro = "Welcome"
blurb_intro = """
This wizard will help you set up some common config options before launching the application.
"""

### SteamPathPage
heading_steam_path = "Steam path"
blurb_steam_path = """
DZGUI needs to find the location to your default Steam installation.
This will be used to determine whether (and where) DayZ is installed.
"""
desc_default_path = "This is the default Steam path on <b>most distributions</b>."
desc_flatpak_path = (
    "This is the default Steam path if you are using <b>Flatpak Steam</b>."
)
desc_ubuntu_path = "This is the default Steam path on <b>Ubuntu-based systems</b>."
desc_debian_path = "This is the default Steam path on <b>Debian-based systems</b>."
no_valid_paths = (
    "No valid Steam paths found on system. Please install Steam to continue."
)
button_scan = "Scan for Steam"

### ConfigMigrationPage
heading_config = "Import files"
blurb_config = """
It looks like you have a DZGUI 6 configuration file on the system.\n
Would you like to import this into DZGUI 7, keeping your existing preferences?\n
In both cases, your DZGUI 6 file will persist separately from DZGUI 7.
"""
config_import_button = "Import DZGUI 6 config to DZGUI 7"
config_import_box = (
    "Configuration data imported successfully. Proceed to the next step."
)
config_new_button = "Create new DZGUI 7 config from scratch"
config_new_box = "A new config file will be created. Proceed to the next step."
config_error_box = "Something went wrong while writing a new config file to the system."

### APIValidationPage
entry_placeholder = "Enter API key here"
api_success = "API key set successfully. Please proceed to the next step."
heading_steam_api = "Steam Web API key"
button_web_api = "Web API setup link"
blurb_steam_api = """
You must set up a Steam Web API key in order to browse the global server list.
\nIf you don't have one already, it can be set up via the page below.
\nPlease refer to the DZGUI documentation for more instructions.
"""

### PreferencesPage
heading_prefs = "User preferences"
blurb_prefs = """Here you can set up some basic settings. Additional preferences can be\n
configured via the Options menu once DZGUI launches.
"""
label_player = "Player name"
placeholder_player = "Set an in-game player name"
radio_km = "km (kilometers)"
radio_mi = "mi (miles)"
label_dist = "Distance display"
label_client = "Steam client"

### Shortcuts page
heading_shortcuts = "Create shortcuts"
blurb_shortcuts = (
    "You can optionally create shortcuts to facilitate launching DZGUI faster."
)
button_shortcuts = "Create shortcuts"
checkbox_steam_shortcut = (
    "Add DZGUI to Steam library",
    (
        "This creates a standalone copy of DZGUI and adds it to Steam. "
        "You <b>must restart Steam</b> for the shortcut to appear. This will not replace or update existing shortcuts. "
        "If you update DZGUI when it is launched via Steam, updates will be applied to the Steam version."
    ),
)
checkbox_start_menu = (
    "Add a start menu shortcut",
    "Depends on local window manager settings. Will work on Steam Deck.",
)
checkbox_desktop_shortcut = ("Add a desktop shortcut", "Depends on the option above.")

### Completion page
heading_completion = "Setup complete"
blurb_completion = "Configuration completed successfully. Click 'Close' to close this dialog and launch DZGUI."
