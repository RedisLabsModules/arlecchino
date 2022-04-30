#!/bin/sh
''''[ ! -z $VIRTUAL_ENV ] && exec /opt/redislabs/bin/python -O -u -- "$0" ${1+"$@"}; command -v /opt/redislabs/bin/python3 > /dev/null && exec /opt/redislabs/bin/python3 -O -u -- "$0" ${1+"$@"}; exec /opt/redislabs/bin/python2 -O -u -- "$0" ${1+"$@"} # '''

from __future__ import print_function
import os
import sys
from zipfile import ZipFile
from tarfile import TarFile
import yaml
from shutil import copy2, copytree, rmtree
from pathlib import Path
from contextlib import contextmanager
import urllib
import gzip
import shutil
import platform
import argparse
import json
from collections import OrderedDict
import tempfile
import subprocess
from textwrap import dedent

from rlec_auto import *

sys.path.insert(0, "/opt/readies")
import paella

#----------------------------------------------------------------------------------------------

S3_ROOT="http://s3.amazonaws.com/redismodules"
DEFAULT_S3_YAML_DIR="preview1"
MOD_DIR="/opt/redislabs/lib/modules"
MODULE_LIB_DIR="/opt/redislabs/lib/modules/lib"
REDIS_LIBS_DIR="/opt/redislabs/lib"
DL_DIR="/tmp"
MOD_PATH_INT_PREFIX="/opt/view/"

#----------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description='Install Redis Modules')
parser.add_argument('--yaml', action="store", help='Configuration file')
parser.add_argument('--s3-dir', action="store", help='Configuration file directory in S3', default=DEFAULT_S3_YAML_DIR)
parser.add_argument('--s3-yaml', action="store", help='Configuration file path in S3')
parser.add_argument('--modinfo', action="store", help='Module info JSON for DB creation')
parser.add_argument('--nop', action="store_true", help='No operation')
parser.add_argument('--no-bootstrap-check', action="store_true", help='void bootstrap check')
parser.add_argument('--verbose', action="store_true", help='Speak aload work working')
args = parser.parse_args()

S3_YAML_DIR = args.s3_dir
NOP = args.nop
VERBOSE = args.verbose

#----------------------------------------------------------------------------------------------

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# this is helpful for iterating over yaml keys in natural order
def ordered_yaml_load(stream, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
    class OrderedLoader(Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    return yaml.load(stream, OrderedLoader)

def wget(url, dest):
    file = os.path.join(dest, os.path.basename(url))
    backup = None
    if NOP:
        print("downloading " + S3_ROOT + "/" + url + " into " + file)
        return file
    if os.path.isfile(file):
        fd, backup_path = tempfile.mkstemp()
        backup_path = backup_path.encode('utf8')
        os.close(fd)
        shutil.move(file, backup_path)
        backup = backup_path
    try:
        print("downloading from " + S3_ROOT + "/" + url)
        urllib.urlretrieve(S3_ROOT + "/" + url, file)
        print("download done.")
        try:
            os.unlink(backup)
        except Exception as x:
            eprint("backup unlink failed: " + str(x))
    except Exception as x:
        eprint("failed to download {}: {}".format(url, str(x)))
        if not backup is None:
            shutil.move(backup, file)
        sys.exit(1)
    return file

if args.yaml is None:
    if not args.s3_yaml is None:
        yaml_s3_path = args.s3_yaml
    else:
        distname = platform.linux_distribution()[0].lower()
        print("This is " + distname)
        if distname == 'centos linux' or distname == 'redhat':
            dist = '-redhat'
        elif distname == 'ubuntu' or distname == 'debian':
            dist = '-debian'
        else:
            dist = ''

        yaml_fname = "redis-modules" + dist + ".yaml"
        yaml_s3_path = S3_YAML_DIR + "/" + yaml_fname

    if not os.path.exists(yaml_fname):
        wget(yaml_s3_path, os.getcwd())
    yaml_path = yaml_fname
else:
    yaml_path = args.yaml

with open(yaml_path, 'r') as stream:
    try:
        MODULES = ordered_yaml_load(stream, yaml.SafeLoader).items()
    except:
        MODULES = {}

@contextmanager
def cwd(path):
    d0 = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(d0)

ZIP_UNIX_SYSTEM = 3

def zip_extract_all_with_permission(zipf, target_dir):
    with ZipFile(zipf, 'r') as zip:
        for info in zip.infolist():
            path = zip.extract(info, target_dir)
            if info.create_system == ZIP_UNIX_SYSTEM:
                unix_attributes = info.external_attr >> 16
                if unix_attributes:
                    os.chmod(path, unix_attributes)

def tar_extract_all(file, target_dir):
    tar = TarFile(file, 'r')
    tar.extractall(target_dir)

def ungzip(gz_file, dest_file):
    with gzip.open(gz_file, 'rb') as f_in:
        with open(dest_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

def extract_all_with_permission(file, target_dir):
    if file.endswith('.zip'):
        zip_extract_all_with_permission(file, target_dir)
    elif file.endswith('.tgz'):
        tar_file = DL_DIR + '/' + os.path.basename(os.path.splitext(file)[0]) + '.tar'
        ungzip(file, tar_file)
        tar_extract_all(tar_file, target_dir)
        os.remove(tar_file)
    elif file.endswith('.tar'):
        tar_extract_all(file, target_dir)

#----------------------------------------------------------------------------------------------

def extract_modinfo(file, mod_args=None):
    if not file.endswith('.zip'):
        return ''
    try:
        with ZipFile(file) as zip:
            with zip.open('module.json') as jf:
                j = json.loads(jf.read())
                if mod_args is None:
                    args = j["command_line_args"]
                else:
                    args = mod_args
                return json.dumps({ "module_name":  j["module_name"], "semantic_version": j["semantic_version"], "module_args": args })
    except:
        eprint("Cannot read module info for " + file)
        return ''

def mkdir_and_chown(dir, owner):
    longdir = dir
    last_missing = ''
    while not os.path.exists(dir):
        last_missing = dir
        dir = os.path.dirname(dir)
        if last_missing == dir:
            break
    if not os.path.exists(longdir):
        os.makedirs(longdir)
    if last_missing != '':
        os.system("chown -R {} {}".format(owner, last_missing))

def install_module(name, mod):
    try:
        dname = ""
        dest = mod.get('dest')
        if dest is not None:
            dest = dest.format(**locals())
        else:
            destfile = mod.get('destfile')
            if destfile is not None:
                dest = os.path.dirname(destfile)
                dname = os.path.basename(destfile)
            else:
                dest = MOD_DIR

        zipf = ''
        unzip = mod.get('unzip')
        if unzip:
            zipdest = DL_DIR
        else:
            zipdest = dest

        if 'path' in mod:
            mod_path = mod['path']
            if not os.path.isabs(mod_path):
                mod_path = MOD_PATH_INT_PREFIX + mod_path
            if NOP:
                if destfile:
                    print("copying {SRC} to {DEST}".format(SRC=mod_path, DEST=destfile))
                else:
                    print("copying {SRC} into {DEST}".format(SRC=mod_path, DEST=zipdest))
            else:
                if dname == "":
                    dname = os.path.basename(mod_path)
                    if dname == "":
                        dname = os.path.basename(os.path.dirname(mod_path))
                dpath = os.path.join(zipdest, dname)
                if os.path.exists(dpath):
                    if os.path.isdir(dpath):
                        rmtree(dpath)
                    else:
                        os.remove(dpath)
                mkdir_and_chown(zipdest, "redislabs:redislabs")
                if os.path.isdir(mod_path):
                    copytree(mod_path, dpath)
                else:
                    copy2(mod_path, dpath)
                    zipf = dpath
                os.system("chown -R redislabs:redislabs {}".format(dpath))
        elif 'awspath' in mod:
            if NOP:
                print("downloading " + mod['awspath'] + " into " + zipdest)
            else:
                mkdir_and_chown(zipdest, "redislabs:redislabs")
                zipf = wget(mod['awspath'], zipdest)
                os.system("chown -R redislabs:redislabs {}".format(zipf))

        if unzip:
            if not os.path.exists(dest):
                if NOP:
                    print("creating " + dest)
                else:
                    os.makedirs(dest)
            if NOP:
                print("extracting " + zipf + " into " + dest)
            else:
                extract_all_with_permission(zipf, dest)
                os.system("chown -R redislabs:redislabs {}".format(dest))

        mod_args = mod['args'] if 'args' in mod else ''

        if 'exec' in mod:
            cmd = "{{ {}; }} >{} 2>&1".format(mod['exec'], "/tmp/{}-exec.log".format(name))
            os.system(cmd)

        modinfo = ''
        if zipf != '':
            modinfo = extract_modinfo(zipf, mod_args)
        if modinfo != '' and is_bootstrapped:
            print("Uploading module to cluster...")
            script_base = """
                import sys
                import traceback
                import time
                import logging
                try:
                    # rlec 5.6+
                    from cnm import CCS
                    from cnm.restclient import RESTClient
                    from cnm.services.resource_mgr.resource_mgr import ResourceManagerAPI
                except:
                    # rlec 5.4
                    sys.path.insert(0, "/opt/redislabs/lib/cnm")
                    sys.path.insert(0, "/opt/redislabs/lib/cnm/python")
                    import CCS
                    from restclient import RESTClient

                """

            if mod.get('modules_with_dependencies_api', False):
                script = """
                    def get_module(module_filepath):
                        from cnm.redis_module import RedisModule
                        try:
                            RedisModule.remote_install(module_filepath, timeout=60)
                            return 0
                        except Exception as x:
                            print("Failed to install module: %s" % x)
                            print(traceback.format_exc())
                            return 1

                    if len(sys.argv) > 0:
                        sys.exit(get_module(sys.argv[1]))
                    """
            if mod.get('modules_v2_api', True):
                script = """
                    def get_module(module_filepath):
                        ccs = CCS.Context()
                        default_logger = logging.getLogger(__name__)
                        rest_client = RESTClient(ccs, api_host="localhost", version='v2', timeout=600)
                        with open(module_filepath, 'rb') as module_file:
                            response = rest_client.post("/modules",
                                                        files={'module': module_file},
                                                        params={'is_bundled': False})
                            j = response.json()
                            # if not response.ok: # and j.get('error_code') != 'module_exists':
                            #     print(j.get('description'))
                            # exit(0 if response.ok else 1)

                            if response.status_code != 201 and response.status_code != 202:
                                return False
                            install_task_id = j['action_uid']
                            resource_mgr_api = ResourceManagerAPI(ccs, default_logger)
                            tasks = []
                            for i in range(120 * 10):
                                time.sleep(0.1)
                                tasks = resource_mgr_api.get_tasks(task_id=install_task_id)
                                if tasks == []:
                                    return True
                                finished = ResourceManagerAPI.task_completed(tasks[0])
                                if finished:
                                    status = tasks[0].get('status')
                                    exit(1 if status != 'completed' else 0)
                            exit(0 if response.ok else 1)

                    if len(sys.argv) > 0:
                        sys.exit(get_module(sys.argv[1]))
                    """
            else:
                script = """
                    def get_module(module_filepath):
                        ccs = CCS.Context()
                        rest_client = RESTClient(ccs, api_host="localhost", timeout=600)
                        with open(module_filepath, 'rb') as module_file:
                            response = rest_client.post("/modules",
                                                        files={'module': module_file},
                                                        params={'is_bundled': False})
                            j = response.json()
                            if not response.ok: # and j.get('error_code') != 'module_exists':
                                print(j.get('description'))
                            exit(0 if response.ok else 1)

                    if len(sys.argv) > 0:
                        sys.exit(get_module(sys.argv[1]))
                    """
            fd, script_path = tempfile.mkstemp()
            _script = dedent(script_base) + dedent(script)
            if sys.version_info > (3, 0):
                _script = _script.encode()
            os.write(fd, _script)
            os.close(fd)
            try:
                xx = subprocess.check_output('/bin/bash -c \'/opt/redislabs/bin/python -O {} {}\''.format(script_path, zipf), shell=True)
                if VERBOSE:
                    print(xx)
            except subprocess.CalledProcessError as x:
                eprint("Error: " + x.output)
                modinfo = ''
            os.unlink(script_path)

        return modinfo
    except Exception as x:
        eprint(str(x))
        return ''

def install_modules():
    modspec = ''
    if args.modinfo and os.path.exists(args.modinfo):
        os.remove(args.modinfo)
    if MODULES is None:
        return ''
    for mod, modval in MODULES:
        print("Installing " + mod + "...")
        modinfo = install_module(mod, modval)
        if not modinfo.strip():
            continue
        if not modspec:
            modspec = modinfo
        else:
            modspec = modspec + ', ' + modinfo
    if not args.modinfo is None:
        with open(args.modinfo, 'w') as file:
            file.write(modspec)

def create_so_links():
    if NOP:
        print("creating .so symlinks...")
        return
    if not os.path.exists(MOD_DIR + '/lib'):
        return
    with cwd(MOD_DIR + '/lib'):
        for f in Path('.').glob('**/*.so*'):
            src = 'modules/lib/' + str(f)
            dest = REDIS_LIBS_DIR + '/' + os.path.basename(str(f))
            if os.path.exists(dest):
                os.remove(dest)
            os.symlink(src, dest)

#----------------------------------------------------------------------------------------------

is_bootstrapped = os.path.exists('/etc/opt/redislabs/node.id') or os.path.exists('/var/opt/redislabs/ephemeral_config/node.id')

if not os.path.exists('/opt/redislabs/lib/modules'):
    eprint("Cluster does not support module bundling. Aborting")
    sys.exit(1)

install_modules()
create_so_links()
print("Done.")
