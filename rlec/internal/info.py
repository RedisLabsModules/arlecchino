#!/bin/sh
''''[ ! -z $VIRTUAL_ENV ] && exec /opt/redislabs/bin/python -O -u -- "$0" ${1+"$@"}; command -v /opt/redislabs/bin/python3 > /dev/null && exec /opt/redislabs/bin/python3 -O -u -- "$0" ${1+"$@"}; exec /opt/redislabs/bin/python2 -O -u -- "$0" ${1+"$@"} # '''

import sys
import os
import argparse
import json

from rlec_auto import *

sys.path.insert(0, "/opt/readies")
import paella

parser = argparse.ArgumentParser(description='Add RLEC node')
parser.add_argument('--dict', action="store_true", help='Reply with dict for single key query')
parser.add_argument('keys', type=str, action='store', nargs="+", help='Query keys') 
args = parser.parse_args()

info = Info()
resp = {}
if 'nodes-by-ip' in args.keys:
    resp['nodes-by-ip'] = info.nodes_by_ip()

if len(args.keys) == 1 and not args.dict:
    resp = resp[args.keys[0]]
print(json.dumps(resp))
exit(0)
