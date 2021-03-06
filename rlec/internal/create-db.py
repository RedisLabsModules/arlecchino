#!/bin/sh
''''[ ! -z $VIRTUAL_ENV ] && exec /opt/redislabs/bin/python -O -u -- "$0" ${1+"$@"}; command -v /opt/redislabs/bin/python3 > /dev/null && exec /opt/redislabs/bin/python3 -O -u -- "$0" ${1+"$@"}; exec /opt/redislabs/bin/python2 -O -u -- "$0" ${1+"$@"} # '''

import sys
import os
import jinja2
import subprocess
import json
import yaml
import psutil
import shutil
import argparse
import requests
import re
import inspect

from cnm import cnm_config

from rlec_auto import *

sys.path.insert(0, "/opt/readies")
import paella
BB()

rlec_version = paella.Version(cnm_config.cnm_version)

#----------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description='Create database')
parser.add_argument('--id', type=int, default=1, help='ID of database')
parser.add_argument('-n', '--name', type=str, default='db', help='Name of database')
parser.add_argument('-m', '--memory', type=str, default='1g', help='Amount of RAM (default: 1g/1024m)')
parser.add_argument('-s', '--shards', type=int, default=1, help='Number of shards')
parser.add_argument('-f', '--filename', type=str, default='db.yml', help='Database parameters filename')
parser.add_argument('--sparse', action="store_true", help="Sparse shard placement")
parser.add_argument('--replication', action="store_true", help="Enable replication")
parser.add_argument('--flash', type=str, help="Enable Radis on Flash of given size")
parser.add_argument('--modules', type=str, help='File specifying modules with arguments for loading')
parser.add_argument('--no-modules', action="store_true", help="Do not install modules")
parser.add_argument('--verbose', action="store_true", help='Show output of all commands')
args = parser.parse_args()

#----------------------------------------------------------------------------------------------

class Database:
    def __init__(self):
        pass

    @staticmethod
    def create():
        pass

#----------------------------------------------------------------------------------------------

def memunit_to_bytes(mem):
    try:
        x = list(filter(lambda x: len(x) > 1, [mem.split(s) for s in mem_units.keys()]))
        if x == []:
            x = list(filter(lambda x: len(x) > 1, [mem.split(s[0]) for s in mem_units.keys()]))
            if x == []:
                return None
        val = x[0][0]
        u1 = list(filter(lambda x: len(x) > 1, [mem.split(val) for s in mem_units.keys()]))[0][1]
        unit = mem_units[list(filter(lambda x: u1 in x, mem_units))[0]]
        return int(val) * unit
    except:
        return None

def remove_comments(s):
    return "\n".join(list(map(lambda x: re.sub(r'^#.*$', '', x), s.split("\n"))))

def join_blank_lines(s):
    return re.sub(r'\s+\n', '\n', s)

def meld(template):
    if template[0] == '\n':
        template = template[1:-1]
    t = remove_comments(template)
    s = jinja2.Template(t).render(inspect.currentframe().f_back.f_locals)
    return join_blank_lines(s)

#----------------------------------------------------------------------------------------------

print("\nCreating database...")

db_id = args.id
port = 12000 + db_id - 1

if args.shards > 1:
    sharding = 'true'
    shards = args.shards
else:
    sharding = 'false'
    shards = 1

replication = 'true' if args.replication else 'false'

mem_units = {"kb": 10**3, "mb": 10**6, "gb": 10**9, "tb": 10**12}

mem_bytes = memunit_to_bytes(args.memory)
if mem_bytes is None:
    mem_bytes = memunit_to_bytes('1g')
# mem_mb = int(args.memory) * 1024
mem_bytes_avail = int(psutil.virtual_memory().available/(1024**2)*0.85*(1024**2))
mem_bytes = min(mem_bytes_avail, mem_bytes)
mem_bytes = max(1024**2 * 512, mem_bytes)

flash = args.flash != "" and args.flash is not None
bigstore = "true" if flash is True else "false"
bigstore_ram_size_bytes = memunit_to_bytes(args.flash)
if bigstore_ram_size_bytes is None:
    bigstore_ram_size_bytes = 0

shards_placement = 'sparse' if args.sparse else 'dense'

v1_fields_t = r'''
name: {{args.name}}
port: {{port}}
memory_size: {{mem_bytes}}
sharding: {{sharding}}
shards_count : {{shards}}
shard_key_regex: 
  - regex: ".*\\{(?<tag>.*)\\}.*"
  - regex: "(?<tag>.*)"
replication: {{replication}}
shards_placement: {{shards_placement}}
proxy_policy: all-nodes
# data_persistence: aof
# aof_policy: appendfsync-always
hash_slots_policy: 16k
{{modules_defs}}
{{flash_defs}}
'''

v2_fields_t = r'''
bdb:
  name: {{args.name}}
  port: {{port}}
  memory_size: {{mem_bytes}}
  sharding: {{sharding}}
  shards_count: {{shards}}
  shard_key_regex:
    - regex: ".*\\{(?<tag>.*)\\}.*"
    - regex: "(?<tag>.*)"
  replication: {{replication}}
  shards_placement: {{shards_placement}}
  proxy_policy: all-nodes
  data_persistence: aof
# data_persistence: snapshot
  aof_policy: appendfsync-always
  hash_slots_policy: 16k
  {{modules_defs}}
  {{flash_defs}}
# {{recovery_plan}}
'''

# "port": 16379,
# "oss_cluster": false,
# "proxy_policy": "single",

fields_flash_t = r'''
bigstore: {{bigstore}}
bigstore_ram_size: {{bigstore_ram_size_bytes}}
'''

recovery_plan_t = r'''
recovery_plan:
  data_files:
    - shard_slots: 0-16383
      node_uid: 1
      filename: /opt/view/rlec/in/db-1-1.aof
'''

if rlec_version < paella.Version('6.0.8'):
    api_ver = "v1"
    fields_t = v1_fields_t
else:
    api_ver = "v2"
    fields_t = v2_fields_t

if not args.no_modules and os.path.exists('/opt/view/rlec/modules.json'):
    mod_list = paella.fread('/opt/view/rlec/modules.json')
    modules_defs = 'module_list: [%s]' % mod_list
else:
    modules_defs = ''

flash_defs = meld(fields_flash_t) if flash else ''
recovery_plan = meld(recovery_plan_t)

q = json.dumps(yaml.safe_load(meld(fields_t)))

paella.fwrite('/opt/view/rlec/create-db.rest', q)

with no_ssl_verification():
    res = requests.post('https://localhost:9443/{api_ver}/bdbs'.format(api_ver=api_ver),
                        data=q, headers={'Content-Type': 'application/json'}, auth=('a@a.com', 'a'))
resj = json.loads(res.content)
paella.fwrite('/opt/view/rlec/db.json', json.dumps(resj, indent=4))

if not args.no_modules:
    try:
        modyml = yaml_load('/opt/view/rlec/redis-modules.yml')
    except:
        try:
            modyml = yaml_load('/opt/view/rlec/redis-modules.yaml')
        except:
            eprint("redis-modules.yml file not found")
            modyml = None
    if modyml is not None:
        modnames = modyml.keys()
        if len(modnames) > 0:
            log = paella.sh('egrep -i "{}" /var/opt/redislabs/log/*'.format("|".join(modnames)), fail=False)
            paella.fwrite('/opt/view/rlec/db-create.log', log)
    else:
        eprint("Modules not loaded")

if os.path.exists('/opt/view/rlec/db.json'):
    if 'error_code' in resj:
        if resj['error_code'] != "":
            eprint("There are errors:")
            eprint(resj['description'])
            exit(1)
else:
    print("There are errors.")
    exit(1)

paella.rm_rf('/opt/view/rlec/cnm_exec.log')
shutil.copy('/var/opt/redislabs/log/cnm_exec.log', '/opt/view/rlec')
sh("chmod 666 /opt/view/rlec/cnm_exec.log")
print('Done.')
exit(0)
