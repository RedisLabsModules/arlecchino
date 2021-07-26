import os
import sys
import os.path
import argparse
import subprocess
import time
from glob import glob
import json
from multiprocessing import Pool

READIES = "/w/rafi_1/readies"
sys.path.insert(0, READIES)
import paella

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

RLEC_DOCKERS = {
        'bionic-master': {'image': 'redislabs/redis-internal:100.0.0-2199.bionic', 'cnmver': '100.0.0-2199'},
        'centos-master': {'image': 'redislabs/redis-internal:100.0.0-2066.rhel7', 'cnmver': '100.0.0-2066'},
        'centos8-master': {'image': 'redislabs/redis-internal:100.0.5-3996.rhel8', 'cnmver': '100.0.5-3996'},
        'bionic-1857':   {'image': 'redislabs/redis-internal:100.0.0-1857.bionic', 'cnmver': '100.0.0-1857'},
        'centos-1922':   {'image': 'redislabs/redis-internal:100.0.0-1922.rhel7', 'cnmver': '100.0.0-1922'},
        'bionic-6.0.9':  {'image': 'redislabs/redis-internal:6.0.9-2.bionic', 'cnmver': '6.0.9-2'},
        'bionic-6.0.6':  {'image': 'redislabs/redis:6.0.6-39.bionic', 'cnmver': '6.0.6-39'},
        'bionic-5.6.0':  {'image': 'redislabs/redis-internal:5.6.0-30.bionic', 'cnmver': '5.6.0-30'},
        'centos-5.6.0':  {'image': 'redislabs/redis-internal:5.6.0-30.rhel7', 'cnmver': '5.6.0-30'},
        'bionic-5.4.14': {'image': 'redislabs/redis-internal:5.4.14-19.bionic', 'cnmver': '5.4.14-19'},
        'centos-5.4.14': {'image': 'redislabs/redis-internal:5.4.14-19.rhel7', 'cnmver': '5.4.14-19'},
        'bionic-5.4.11': {'image': 'redislabs/redis-internal:5.4.11-2.bionic', 'cnmver': '5.4.11-2'},
    }

#----------------------------------------------------------------------------------------------

class DockerHost:
    def __init__(self):
        try:
            self.host = os.environ.get("DOCKER_HOST").split(':')[0]
        except:
            self.host = 'localhost'

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

class RLEC:
    def __init__(self, docker_os=None):
        # when views are on nfs and using rancheros (obviously, a hack)
        self.rlec_view_root = None
        if not os.getenv("RANCHEROS_RLEC") is None:
            self.rlec_view_root="/mnt/nfs-1"

        here = os.path.dirname(paella.current_filepath())
        self.view = paella.relpath(here, '../../..')
        self.viewname = os.path.basename(self.view)
        
        if self.rlec_view_root is None:
            self.rlec_view_root = paella.relpath(self.view, '..')

        self.internal = '/opt/view/modullaneous/rlec-docker/internal'
        # self._fix_rlec_dir()

        self._determine_docker_os(docker_os)
        self.docker_image = RLEC_DOCKERS[self.docker_os]["image"]
        self.cnm_version = RLEC_DOCKERS[self.docker_os]["cnmver"]
        
        self.debug = os.getenv('DEBUG', '') == '1'
        self.slow = os.getenv('SLOW', '') == '1'
        self.verbose = os.getenv('SHOW', '') == '1' or os.getenv('VERBOSE', '') == '1' or os.getenv('V', '') == '1'

    def _determine_docker_os(self, docker_os):
        if os.path.exists(f"{self.view}/rlec/OS"):
            docker_os_f = paella.fread(f"{self.view}/rlec/OS")
        else:
            docker_os_f = None
        if docker_os is None:
            if docker_os_f is None:
                docker_os = 'bionic-master'
            else:
                docker_os = docker_os_f

        if not docker_os in RLEC_DOCKERS:
            print(f"Invalid OS specified: {docker_os}")
            exit(1)
        if docker_os_f is None or docker_os != docker_os_f:
            paella.fwrite(f"{self.view}/rlec/OS", docker_os)
        self.docker_os = docker_os
            
    def _fix_rlec_dir(self):
        d = os.path.join(self.view, "rlec")
        if not os.path.isdir(d):
            paella.mkdir_p(f"{d}")
            sh(f"chmod 777 {d}")
            sh(f"chmod g+s {d}")
            print(f"Control directory {d} created.")
            print("Note that redis-modules.yaml needs to be created for loading modules.")
        else:
            sh(f"chmod -R 777 {d}")
            sh(f"chmod g+s {d}")

    #------------------------------------------------------------------------------------------

    def cid(self, node_num=1):
        k = node_num - 1
        file = f"{self.view}/rlec/RLEC" + ("" if k == 0 else f".{k}")
        return paella.fread(file).strip()

    def no_internet(self):
        return os.path.exists(f"{self.view}/rlec/NO_INTERNET")

    def is_running(self):
        return os.path.isfile(self.view + "/rlec/RLEC")
    
    def cluster(self):
        if self.is_running():
            cluster = Cluster()
        else:
            cluster = None
        return cluster

    def main_node(self):
        return Node()

    def node_log(self, num):
        return f"{self.view}/rlec/out.{num}"
    
    @staticmethod
    def show_osnicks():
        print("\n".join(sorted(RLEC_DOCKERS.keys())))

    def log(self, text, num=1, new=False):
        paella.fwrite(f"{self.node_log(num)}", text + "\n", mode="w" if new else "a+")
        if self.verbose:
            print(text)

    def fetch_logs(self):
        Cluster().fetch_logs()

    #------------------------------------------------------------------------------------------

    def create_cluster(self, dbname='', shards=1, no_modules=False, no_internet=False,
                       no_patch=False, no_bootstrap=False, keep=False, debug=False):
        if no_internet:
            paella.fwrite(f"{self.view}/rlec/NO_INTERNET", "")
        else:
            try:
                os.unlink(f"{self.view}/rlec/NO_INTERNET")
            except:
                pass
        return Cluster.create(dbname=dbname, shards=1, no_modules=no_modules, no_patch=no_patch,
                              no_bootstrap=no_bootstrap, keep=keep, debug=debug)

    def install_modules(self):
        cluster = self.cluster()
        if not cluster is None:
            cluster.install_modules()
        
    def add_node(self, num=1, no_patch=False, no_join=False):
        try:
            cluster = self.cluster()
            if not cluster is None:
                cluster.add_node(num, no_patch=no_patch, no_join=no_join)
        except Exception as x:
            print(str(x))
            exit(1)

    def add_nodes(self, numbers, no_patch=False, no_join=False):
        try:
            cluster = self.cluster()
            if not cluster is None:
                cluster.add_nodes(numbers, no_patch=no_patch, no_join=no_join)
        except:
            print(full_stack())
            exit(1)
            
    def join_node(self, num):
        try:
            cluster = self.cluster()
            if not cluster is None:
                cluster.join_node(num=num)
        except Exception as x:
            print(str(x))
            exit(1)

    def remove_node(self, num=1, keep=False):
        try:
            cluster = self.cluster()
            if not cluster is None:
                cluster.remove_node(Node(num=num), no_stop=keep)
        except Exception as x:
            print(str(x))
            exit(1)

    def stop_cluster(self):
        if self.cluster() is None:
            return
        Cluster().stop()
        
    def create_db(self, name='db1', shards=3, memory='1g', sparse=False, replication=False):
        cluster = self.cluster()
        if cluster is None:
            return
        cluster.create_db(name=name, shards=shards, memory=memory, sparse=sparse, replication=replication)
    
    #------------------------------------------------------------------------------------------
    
    def exec(self, cmd, uid=None, cid=None, num=None, to_log=True, to_con=None, vars={}, out=False):
        def write_log(out):
            if not num is None:
                self.log(out, num=num)
        
        if not uid is None:
            uid_arg = f"-u {uid}"
        else:
            uid_arg = ""
        if to_con is None:
            to_con = not to_log and not out
        output = ""
        try:
            if num is None:
                num = 1
            if cid is None:
                cid = self.cid(node_num=num)
            env_vars = " ".join([f'{n}="{str(v)}"' for n, v in vars.items()])
            BB()
            if to_log and not self.verbose:
                output = subprocess.check_output(f"docker exec {uid_arg} -t {cid} bash -c '{env_vars} {cmd}'", 
                                                 shell=True, stderr=subprocess.STDOUT, encoding="utf-8")
                if to_con:
                    print(output)
                if to_log:
                    write_log(output)
            else:
                if self.verbose:
                    print(f"Executing: " + f"docker exec {uid_arg} -t {cid} bash -c '{env_vars} {cmd}'")
                subprocess.check_call(f"docker exec {uid_arg} -t {cid} bash -c '{env_vars} {cmd}'", shell=True)
            if out:
                return 0, output
            else:
                return 0
        except subprocess.CalledProcessError as x:
            BB()
            if to_log:
                write_log(output)
            if out:
                return x.returncode, output
            else:
                return x.returncode

    def iexec(self, cmd, uid=None, cid=None, num=None, vars={}, out=False):
        return self.exec(f"{self.internal}/{cmd}", uid=uid, cid=cid, num=num, vars=vars, out=out)

#----------------------------------------------------------------------------------------------

class Cluster:
    def __init__(self):
        self.rlec = RLEC()

    @staticmethod 
    def create(dbname='', shards=1, no_modules=False, no_patch=False, no_bootstrap=False, keep=False, debug=False):
        rlec = RLEC()
        try:
            if rlec.is_running():
                print("RLEC cluster already running.")
                return False
            node = Node.create(no_patch=no_patch)
           
            # if not no_modules:
            #     print("Installing modules...")
            #     self.install_modules()
            #     print("Done.")
            # else:
            #     try:
            #         os.unlink(f"{rlec.view}/rlec/modules.json")
            #     except:
            #         pass
            BB()
            if no_bootstrap:
                print("One node created (non-bootstrapped state).")
                return Cluster()
            else:
                vars = {'NODE_NUM': node.num}
                if debug:
                    vars['BB'] = '1'
                if rlec.iexec("create-cluster.py", num=1, uid=0, vars=vars) != 0:
                    raise RuntimeError("failed to create cluster")

                print("Cluster created.")

                dhost = DockerHost().host
                print(f"Can be managed via https://{dhost}:8443")
            return Cluster()
        except Exception as x:
            try:
                if not keep:
                    rlec.stop_cluster()
            except:
                pass
            print(f"Error creating RLEC cluster: {str(x)}")
            exit(1)

    #------------------------------------------------------------------------------------------

    def node_numbers(self):
        return [int(f.split('.')[-1]) + 1 for f in glob(f"{self.rlec.view}/rlec/RLEC.*")]

    def last_node_num(self):
        nums = self.node_numbers()
        return max(nums) if nums != [] else 1

    #------------------------------------------------------------------------------------------

    def install_modules(self):
        if self.rlec.iexec("deploy-modules", num=1) != 0:
            raise RuntimeError("failed to create cluster")
    
    def stop(self):
        n = len(self.node_numbers())
        if n > 0:
            print(f"Stopping node{'s' if n > 1 else ''} {', '.join([str(n) for n in self.node_numbers()])} ...")
            xmap(lambda num: Node(num=num).stop(), self.node_numbers())
        # for num in self.node_numbers():
        #     Node(num=num).stop()
        print(f"Stopping node 1 ...")
        Node().stop()
        print(f"Done.")

    def nodes_info_by_ip(self, ip=None):
        rlec = self.rlec
        rc, info = rlec.iexec("info.py nodes-by-ip", out=True)
        if rc != 0:
            raise RuntimeError("failed to get node info")
        info = json.loads(info)
        if ip is None:
            return info
        return info[ip] if ip in info else None

    def add_node(self, num=1, no_patch=False, no_join=False):
        rlec = self.rlec
        node = Node.create(num=num, no_patch=no_patch)
        if not no_join:
            self.join_node(node=node)

    def add_nodes(self, node_numbers, no_patch=False, no_join=False):
        if len(node_numbers) < 1:
            node_numbers = [self.last_node_num() + 1]
        BB()
        xmap(lambda num: self.add_node(num=num, no_patch=no_patch, no_join=True), node_numbers)
        if not no_join:
            print("Joining nodes...")
            for num in node_numbers:
                self.join_node(num=num)
            print("Done.")
    
    def join_node(self, num=None, node=None):
        if node is None:
            node = Node(num=num)
        rlec = self.rlec
        cluster_ip = rlec.main_node().ip()
        if rlec.iexec(f"join-cluster.py {cluster_ip}", num=num, uid=0, cid=node.cid) != 0:
            # subprocess.check_output(f"docker stop {node.cid}", shell=True, stderr=subprocess.STDOUT)
            raise RuntimeError(f"Node {node.num}: failed to join cluster")

    def remove_node(self, node, no_stop=False):
        rlec = self.rlec
        node_info = self.nodes_info_by_ip(node.ip())
        if node_info is None:
            print(f"Node {node.num} is not in cluster")
        else:
            id = node_info["id"]
            if rlec.exec(f"rladmin node {id} remove", num=node.num, to_log=False) != 0:
                print(f"Failed to remove node {node.num} from cluster")
        if not no_stop:
            node.stop()
        else:
            raise RuntimeError(f"Node {node.num}: failed to remove from cluster")
    
    def create_db(self, name='db1', shards=3, memory='1g', sparse=False, replication=False):
        try:
            rlec = self.rlec
            sparse_arg = "--sparse" if sparse else ""
            repl_arg = "--replication" if replication else ""
            if rlec.iexec(f"create-db.py --name={name} --shards={shards} --memory='{memory}' {sparse_arg} {repl_arg}",
                          num=1, vars={'BB': '1'}) == 0:
                rlec.iexec("rediscli-info.py", num=1, uid=0)
        except Exception as x:
            raise RuntimeError(f"Cannot create database: {str(x)}")

    def drop_db(slef, name="db1"):
        pass
        #try:
        #    rlec.iexec(f"drop-db.py --name={name}", num=1) == 0:
        #except Exception as x:
        #    raise RuntimeError(f"Cannot drop database: {str(x)}")
        
    def fetch_logs(self):
        Node(num=1).fetch_logs()
        for node_num in self.node_numbers():
            node = Node(num=node_num)
            node.fetch_logs()

#----------------------------------------------------------------------------------------------

class Node:
    def __init__(self, num=1, cid=None):
        self.rlec = RLEC()
        self.num = num
        if not cid is None:
            self.cid = cid
        else:
            self.cid = self.rlec.cid(num)
        self.cid_file = f"{self.rlec.view}/rlec/RLEC" + ("" if num == 1 else f".{num-1}")

    @staticmethod 
    def create(num=1, no_patch=False):
        cid = None
        rlec = RLEC()
        try:
            if num > 1 and not rlec.is_running():
                print("RLEC cluster not running.")
                return False

            no_inet = "--network no-internet" if rlec.no_internet() else ""
            vol = f"-v {rlec.rlec_view_root}:/v"

            k = num - 1
            ports = f"-p {8443+k}:8443 -p {9443+k}:9443 -p {12000+k}:12000 -p {6379+k}:6379"
            
            BB()
            rlec.log(f"Creating from {rlec.docker_image}", new=True)
            debug_opt = "--privileged --ulimit core=-1 --security-opt seccomp=unconfined"
            cid = sh(f"docker run -d {debug_opt} --cap-add sys_resource {no_inet} {ports} {vol} {rlec.docker_image}")
            # time.sleep(5)
            # docker inspect -f '{{.State.Running}}'
            cid_file = f"{rlec.view}/rlec/RLEC" + ("" if num == 1 else f".{k}")
            paella.fwrite(cid_file, cid)
            rlec.log(f"Created docker {cid}")

            vars = {}
            if no_patch:
                vars["NO_PATCH"] = 1
            if rlec.no_internet():
                vars["NO_INTERNET"] = 1
            vars["NODE_NUM"] = num
            vars["CNM_VER"] = rlec.cnm_version
            
            print(f"Preparing node {num}...")
            rlec.exec(f"/v/{rlec.viewname}/modullaneous/rlec-docker/internal/rlec-fixes", num=num, uid=0, cid=cid, vars=vars)
            print(f"Node {num} created.")

            return Node(num=num, cid=cid)
        except:
            if not cid is None:
                subprocess.check_output(f"docker stop {cid}", shell=True, stderr=subprocess.STDOUT)
                subprocess.check_output(f"docker rm {cid}", shell=True, stderr=subprocess.STDOUT)
            print("Error creating RLEC node")
            exit(1)

    #------------------------------------------------------------------------------------------

    def exists(self):
        return os.path.exists(self.cid_file)

    def ip(self):
         return sh(['docker', 'inspect', '-f', '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}', f"{self.cid}"]).strip()

     #------------------------------------------------------------------------------------------

    def stop(self):
        try:
            subprocess.check_output(f"docker stop {self.cid}", shell=True, stderr=subprocess.STDOUT)
            subprocess.check_output(f"docker rm {self.cid}", shell=True, stderr=subprocess.STDOUT)
        except:
            pass
        try:
            os.unlink(self.cid_file)
        except:
            pass

    def fetch_logs(self):
        self.rlec.exec(f"cp /var/opt/redislabs/log/cnm_http.log /opt/view/rlec/cnm_http.log.{self.num}", num=self.num)
        self.rlec.exec(f"cp /var/opt/redislabs/log/cnm_exec.log /opt/view/rlec/cnm_exec.log.{self.num}", num=self.num)
        self.rlec.exec(f"cp /var/opt/redislabs/log/resource_mgr.log /opt/view/rlec/resource_mgr.log.{self.num}", num=self.num)

#----------------------------------------------------------------------------------------------
