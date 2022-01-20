#!/bin/sh
''''[ ! -z $VIRTUAL_ENV ] && exec /opt/redislabs/bin/python -O -u -- "$0" ${1+"$@"}; command -v /opt/redislabs/bin/python3 > /dev/null && exec /opt/redislabs/bin/python3 -O -u -- "$0" ${1+"$@"}; exec /opt/redislabs/bin/python2 -O -u -- "$0" ${1+"$@"} # '''

import os
import sys
import subprocess
import time
import argparse


from rlec_auto import *

sys.path.insert(0, "/opt/readies")
import paella

RLEC_CLUSTER_NAME = "rlec1"
RLEC_USER = "a@a.com"
RLEC_PWD = "a"

output = ""

#----------------------------------------------------------------------------------------------

def try_bootstrap(args):
    flash = args.flash != "" and args.flash is not None
    global output
    try:
        env1 = os.environ.copy()
        env1["SEC"] = "30"
        subprocess.check_call(['/opt/view/arlecchino/rlec/internal/wait-for-service', 'cnm_http_ctl'], env=env1)
        cmd = ['/opt/redislabs/bin/rladmin', 'cluster', 'create', 
               'name', RLEC_CLUSTER_NAME, 
               'username', RLEC_USER, 'password', RLEC_PWD]
        if args.flash != "":
             cmd += ['flash_enabled', 'flash_path', '/var/opt/redislabs/flash']
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        subprocess.check_call(['/opt/view/arlecchino/rlec/internal/wait-for-service', 'ccs'])
        
        # select latest redis-server as default
        latest_redis = paella.sh('ls /opt/redislabs/bin/redis-server-* | grep -E "redis-server-[0-9]+\.[0-9]+$" | cut -d- -f3 | sort -n -r | head -1')
        paella.sh("rladmin tune cluster redis_upgrade_policy latest")
        paella.sh("rladmin tune cluster default_redis_version {ver}".format(ver=latest_redis))

        return True
    except subprocess.CalledProcessError as x:
        return False

#----------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description='Create cluster')
parser.add_argument('--flash', type=str, help="Enable Radis on Flash of given size")
parser.add_argument('--verbose', action="store_true", help='Show output of all commands')
args = parser.parse_args()

print("Bootstrapping cluster...")
for i in range(3):
    if try_bootstrap(args=args):
        print("Done.")
        exit(0)
    time.sleep(3)
print("Failed to bootstrap:")
print(output)
exit(1)
