import json
import logging
import subprocess

from shlex import shlex
from pathlib import Path

from dzgui.const.constants import APP_NAME
from dzgui.util.bash import concat_bash_args


logger = logging.getLogger(APP_NAME)


def query_defunct() -> None:
    pass


# TODO: unimplemented
# cf.
#!/usr/bin/env bash
# query_defunct(){
#    readarray -t modlist <<< "$@"
#    local max=${#modlist[@]}
#    concat(){
#        for ((i=0;i<$max;i++)); do
#            echo "publishedfileids[$i]=${modlist[$i]}&"
#        done | awk '{print}' ORS=''
#    }
#    payload(){
#        echo -e "itemcount=${max}&$(concat)"
#    }
#    post(){
#        curl -s \
#            -X POST \
#            -H "Content-Type:application/x-www-form-urlencoded"\
#            -d "$(payload)" 'https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/?format=json'
#    }
#    post | jq
#    return
#    local result=$(post | jq -r '
#    .[].publishedfiledetails[]
#    | select(.result==1)
#    | select(.filename|contains("screenshot")|not)
#    | "\(.file_size) \(.publishedfileid)"')
#    <<< "$result" awk '{print $2}'
# }
#
# query_defunct "3576065083"


def concat_mods(mods: list[str]) -> str:
    for mod in mods:
        mods[mod] = f"@{mod}"
    return ";".join(mods)


# TEST: set config to name=user, use official server and no mods,
# ensure that formatted string is identical to fixture
def connect(addr: str, appid: int, name: str, mods: list) -> None:
    # TODO: get name from configs
    # TODO: concat_mods(mods):
    # @<mod>;@<mod>;
    params = [
        f"-connect={addr}",
        "-nolauncher",
        "-nosplash",
        "-skipintro",
        f"-name={name}",
        f"-mod={concat}",
    ]
    # TODO: get steam launch command from configs
    # args = concat_bash_args()
    #
    proc = subprocess.Popen([*args, "-applaunch", appid, *params])
    # check proc.returncode


def find_user_id(path: Path) -> str | None:
    resolved_path = path / "config" / "loginusers.vdf"
    try:
        vdf = vdf2json(resolved_path)
        j = json.loads(vdf)
        for user in j["users"]:
            if j["users"][user]["MostRecent"] == "1":
                return user
        return None
    except Exception as e:
        logger.warn(e)
        return None


def vdf2json(path: Path) -> str:
    def _istr(indent, string):
        return (indent * "  ") + string

    jbuf = "{\n"
    indent = 1

    with open(path, "r") as f:
        st = f.read()
    lex = shlex(st)

    while True:
        tok = lex.get_token()
        if not tok:
            return jbuf + "}\n"
        if tok == "}":
            indent -= 1
            jbuf += _istr(indent, "}")
            ntok = lex.get_token()
            lex.push_token(ntok)
            if ntok and ntok != "}":
                jbuf += ","
            jbuf += "\n"
        else:
            ntok = lex.get_token()
            if ntok == "{":
                jbuf += _istr(indent, tok + ": {\n")
                indent += 1
            else:
                jbuf += _istr(indent, tok + ": " + ntok)
                ntok = lex.get_token()
                lex.push_token(ntok)
                if ntok != "}":
                    jbuf += ","
                jbuf += "\n"


def gen_shortcut() -> None:
    # TODO:
    """
    during setup, prompt user to select matching user id from loginusers
    show user account name, select outer steam id
    steam/userdata/<steamid_32>/config/shortcuts.vdf
    """
    # STEAMID_MAGIC = 76561197960265728
    # STEAMID_64 - STEAMID_MAGIC = STEAMID32
    # or get right-most 32 bits
    # STEAMID_64 & 0xFFFFFFFF
    pass
