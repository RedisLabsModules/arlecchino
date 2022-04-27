import os
import sys
import os.path
import argparse
import subprocess
import time
from glob import glob
import json
from multiprocessing import Pool
from urllib.parse import urlparse

HERE = os.path.dirname(__file__)
READIES = os.path.abspath(os.path.join(HERE, "../../readies"))
sys.path.insert(0, READIES)
import paella  # noqa: F401

RLEC_LATEST_VERSION = "6.0.20"
RLEC_LATEST_BUILD = "97"
RLEC_INTERNAL_MASTER_BUILD = 2500

#----------------------------------------------------------------------------------------------

_func = None

def worker_init(func):
    global _func
    _func = func

def worker(x):
    return _func(x)

def xmap(func, iterable, processes=None):
    if os.getenv('SLOW', '') == '1':
        # map(func, iterable)
        for x in iterable:
            func(x)
    else:
        with Pool(processes, initializer=worker_init, initargs=(func,)) as p:
            return p.map(worker, iterable)

def full_stack():
    import traceback, sys
    exc = sys.exc_info()[0]
    stack = traceback.extract_stack()[:-1]  # last one would be full_stack()
    if exc is not None:  # i.e. an exception is present
        # remove call of full_stack, the printed exception
        # will contain the caught exception caller instead
        del stack[-1]
    trc = 'Traceback (most recent call last):\n'
    stackstr = trc + ''.join(traceback.format_list(stack))
    if exc is not None:
        stackstr += '  ' + traceback.format_exc().lstrip(trc)
    return stackstr

#----------------------------------------------------------------------------------------------

RLEC_IMAGE = 'redislabs/redis'
RLEC_INT_IMAGE = 'redislabs/redis-internal'

RLEC_BUILDS = {
    '6.2.2': {},
    '6.0.20': {},
    '6.0.12': {},
    '6.0.8': {},
    '5.6.0': {},
}

RLEC_INT_BUILDS = {
    'master': { 'version': '100.0.0' },
    '100.0.5': {},
    '6.2.2': {},
    '6.0.20': {},
    '6.0.12': {},
    '6.0.8': {},
    '5.6.0': {},
}

RLEC_OS = {
    'trusty': 'trusty',
    'xenial': 'xenial',
    'bionic': 'bionic',
    'centos7': 'rhel7',
    'centos8': 'rhel8'
}

#----------------------------------------------------------------------------------------------

class DockerHost:
    def __init__(self):
        try:
            url = urlparse(os.getenv("DOCKER_HOST", 'tcp://127.0.0.1:2375'))
            self.host = url.hostname
        except:
            self.host = '127.0.0.1'

#----------------------------------------------------------------------------------------------

class Docker:
    pass

class Container:
    def __init__(self, cid):
        pass

    def start(self):
        pass

    def stop(self):
        pass

#----------------------------------------------------------------------------------------------
