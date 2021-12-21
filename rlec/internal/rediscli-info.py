#!/opt/redislabs/bin/python2 -O

import json
import os
import sys
import re
from shutil import copy2

from rlec_auto import *

sys.path.insert(0, "/opt/readies")
import paella

try:
    with open('/opt/view/rlec/db.json', 'r') as jfile:
        j = json.loads(jfile.read()) 
        id = j["uid"]
        redis_conf = '/var/opt/redislabs/redis/redis-' + str(id) +'.conf'
        copy2(redis_conf, '/opt/view/rlec/redis.conf')
        sh("chmod 666 /opt/view/rlec/redis.conf")
except:
    print("Failed to process /opt/view/rlec/db.json")

#    with open(redis_conf, 'r') as conf:
#        line = conf.readline()
#        for line in conf:
#            r = re.search('^port (\d+)', line)
#            if r:
#                print("port " + r.group(1))
#            r = re.search('^requirepass (\d+)', line)
#            if r:
#                print("password " + r.group(1))
