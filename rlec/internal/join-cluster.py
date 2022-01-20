#!/bin/sh
''''[ ! -z $VIRTUAL_ENV ] && exec /opt/redislabs/bin/python -O -u -- "$0" ${1+"$@"}; command -v /opt/redislabs/bin/python3 > /dev/null && exec /opt/redislabs/bin/python3 -O -u -- "$0" ${1+"$@"}; exec /opt/redislabs/bin/python2 -O -u -- "$0" ${1+"$@"} # '''

import sys
import os
import subprocess
import time
import argparse


from rlec_auto import *

sys.path.insert(0, "/opt/readies")
import paella

RLEC_USER = "a@a.com"
RLEC_PWD = "a"

output = ""

#----------------------------------------------------------------------------------------------

def try_join(master_ip, args):
    flash = args.flash
    global output
    try:
        env1 = os.environ.copy()
        env1["SEC"] = "30"
        cmd = ['/opt/redislabs/bin/rladmin', 'cluster', 'join',
               'nodes', master_ip,
               'username', RLEC_USER, 'password', RLEC_PWD,]
        if flash:
            cmd += ['flash_enabled', 'flash_path', '/var/opt/redislabs/flash']
        # subprocess.check_call()
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError as x:
        return False

#----------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description='Join cluster')
parser.add_argument('--flash', action="store_true", help="Enable Radis on Flash")
parser.add_argument('--verbose', action="store_true", help='Show output of all commands')
parser.add_argument('master', metavar='MASTER', nargs=1, help='master IP address')
args = parser.parse_args()

print("Joining cluster...")
for i in range(3):
    if try_join(args.master, args=args):
        print("Done.")
        exit(0)
    time.sleep(3)
print("Failed to join cluster:")
print(output)
exit(1)
