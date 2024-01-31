import sys
import a2s
import math
import json
from a2s import dayzquery
sys.path.append('a2s')

def get_info(ip, qport):
    try:
        info = a2s.info((ip, int(qport)))

        name = info.server_name
        map = info.map_name
        address = ip + ":" + qport
        gameport = str(info.port)
        players = info.player_count
        max_players = info.max_players
        keywords = info.keywords
        ping = (info.ping*1000)
        ping = math.floor(ping)

        res = {}

        res['name'] = name
        res['map'] = map
        res['gametype'] = keywords
        res['players'] = players
        res['max_players'] = max_players
        res['addr'] = address
        res['gameport'] = gameport
        res['stat'] = "online"
        res['qport'] = qport
        res['ping'] = str(ping) + "ms"

        j = json.dumps([res])

        print(j)
    except:
        sys.exit(1)

def get_rules(ip, qport):
    try:
        mods = dayzquery.dayz_rules((ip, int(qport))).mods
        for k in mods:
            print(k.workshop_id)
    except:
        sys.exit(1)

def get_names(ip, qport):
    try:
        mods = dayzquery.dayz_rules((ip, int(qport))).mods
        ids = []
        names = []
        for mod in mods:
            names.append(mod.name)
            ids.append(mod.workshop_id)
        res = {}
        res['names'] = names
        res['ids'] = ids
        j = json.dumps(res)
        print(j)
    except:
        sys.exit(1)

ip = sys.argv[1]
qport = sys.argv[2]
mode = sys.argv[3]

match mode:
    case "info":
        get_info(ip, qport)
    case "rules":
        get_rules(ip, qport)
    case "names":
        get_names(ip, qport)
