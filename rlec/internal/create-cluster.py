#!/opt/redislabs/bin/python2 -O

import os
import sys
import subprocess
import time

from rlec_auto import *

sys.path.insert(0, "/opt/readies")
import paella

RLEC_CLUSTER_NAME = "rlec1"
RLEC_USER = "a@a.com"
RLEC_PWD = "a"

output = ""

def try_bootstrap():
    global output
    try:
        env1 = os.environ.copy()
        env1["SEC"] = "30"
        subprocess.check_call(['/opt/view/arlecchino/rlec/internal/wait-for-service', 'cnm_http_ctl'], env=env1)
        output = subprocess.check_output(['/opt/redislabs/bin/rladmin', 'cluster', 'create', 
                                          'name', RLEC_CLUSTER_NAME, 
                                          'username', RLEC_USER, 'password', RLEC_PWD,
                                          'flash_enabled', 'flash_path', '/var/opt/redislabs/flash'], 
                                         stderr=subprocess.STDOUT)
        subprocess.check_call(['/opt/view/arlecchino/rlec/internal/wait-for-service', 'ccs'])
        return True
    except subprocess.CalledProcessError as x:
        return False

print("Bootstrapping cluster...")
for i in range(3):
    if try_bootstrap():
        print("Done.")
        exit(0)
    time.sleep(3)
print("Failed to bootstrap:")
print(output)
exit(1)
