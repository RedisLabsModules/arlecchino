#!/bin/sh
''''[ ! -z $VIRTUAL_ENV ] && exec /opt/redislabs/bin/python -O -u -- "$0" ${1+"$@"}; command -v /opt/redislabs/bin/python3 > /dev/null && exec /opt/redislabs/bin/python3 -O -u -- "$0" ${1+"$@"}; exec /opt/redislabs/bin/python2 -O -u -- "$0" ${1+"$@"} # '''

import os
import sys
from pathlib import Path
import fnmatch
from shutil import copyfile
import pwd
import grp
import stat
import subprocess
import time

from rlec_auto import *

sys.path.insert(0, "/opt/readies")
import paella

def chown(path, u, g):
    if isinstance(u, int):
        uid = u
    else:
        uid = pwd.getpwnam(u).pw_uid
    if isinstance(g, int):
        gid = g
    else:
        gid = grp.getgrnam(g).gr_gid
    os.chown(path, uid, gid)

def fmod(path):
    return os.stat(path)[stat.ST_MODE]

if len(sys.argv) == 1:
    exit(0)
version = sys.argv[1]
	
src = '/opt/view/arlecchino/rlec/' + version
dest = '/opt/redislabs/lib/python2.7/site-packages'

if not os.path.exists(dest + '/cnm/CNM.pyo'):
    dest = '/opt/redislabs/lib'
    if not os.path.exists(dest + '/cnm/CNM.pyo'):
        print('Cannot locate CNM. Aborting.')
        exit(1)

def sync(name, src, dest):
    print('Looking for custom {} artifacts at {}'.format(name, src))
    if os.path.exists(src):
        print('Found!')
        print('Syching the following artifacts:')
        os.chdir(src)
        for root, dirs, files in os.walk('.'):
            if files == []:
                continue
            s_dir = os.path.realpath(src + '/' + root)
            d_dir = os.path.realpath(dest + '/' + root)
            for f in files:
                sf = s_dir + '/' + f
                df = d_dir + '/' + f
                print(sf + " -> " + df)
                mod = 0o644
                if fnmatch.fnmatch(f, '*.py'):
                    pyo = df + 'o'
                    if os.path.exists(pyo):
                        mod = fmod(pyo)
                        os.unlink(pyo)
                    pyc = df + 'c'
                    if os.path.exists(pyc):
                        mod = fmod(pyc)
                        os.unlink(pyc)
                    print('Done.')
                elif os.path.exists(df):
                    mod = fmod(df)
                copyfile(sf, df)
                if os.path.exists(df):
                    chown(df, 'redislabs', 'redislabs')
                    os.chmod(df, mod)
                    if fnmatch.fnmatch(df, '*.py'):
                        print('/opt/redislabs/bin/python -O -m py_compile ' + df)
                        subprocess.check_call('/opt/redislabs/bin/python -O -m py_compile ' + df, shell=True, stderr=subprocess.STDOUT)
                        chown(pyo, 'redislabs', 'redislabs')
                        if os.path.exists(pyc):
                            chown(pyc, 'redislabs', 'redislabs')

try:
    sync("CNM", src + "/cnm", dest + "/cnm")
    sync("CM", src + "/cm", dest + "/cm")
    exit(0)
except:
    exit(1)
