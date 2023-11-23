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
        address = ip + ":" + str(info.port)
        count = str(info.player_count) + "/" + str(info.max_players)
        keywords = info.keywords
        ping = (info.ping*1000)
        ping = math.floor(ping)

        res = {}

        res['name'] = name
        res['address'] = address
        res['count'] = count
        res['keywords'] = keywords
        res['stat'] = "online"
        res['qport'] = qport
        res['ping'] = str(ping) + "ms"

        j = json.dumps(res)

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

ip = sys.argv[1]
qport = sys.argv[2]
mode = sys.argv[3]

match mode:
    case "info":
        get_info(ip, qport)
    case "rules":
        get_rules(ip, qport)
