#!/opt/redislabs/bin/python2

import sys
import os
import subprocess
import time

RLEC_USER = "a@a.com"
RLEC_PWD = "a"

output = ""

def try_join(master_ip):
    global output
    try:
        env1 = os.environ.copy()
        env1["SEC"] = "30"
        output = subprocess.check_output(['/opt/redislabs/bin/rladmin', 'cluster', 'join', 
        # subprocess.check_call(['/opt/redislabs/bin/rladmin', 'cluster', 'join', 
                                          'nodes', master_ip, 
                                          'username', RLEC_USER, 'password', RLEC_PWD,
                                          'flash_enabled', 'flash_path', '/var/opt/redislabs/flash'], 
                                         stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError as x:
        return False

master_ip = sys.argv[1]
print("Joining cluster...")
for i in range(3):
    if try_join(master_ip):
        print("Done.")
        exit(0)
    time.sleep(3)
print("Failed to join cluster:")
print(output)
exit(1)
