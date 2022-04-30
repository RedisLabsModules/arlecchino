
from .common import *

g_rlec = None

#----------------------------------------------------------------------------------------------

def global_rlec(rlec=None):
    global g_rlec
    if rlec is not None:
        g_rlec = rlec
    elif g_rlec is None:
        g_rlec = RLEC()
    return g_rlec

def newdict(d, d2):
    d1 = d.copy()
    d1.update(d2)
    return d1

#----------------------------------------------------------------------------------------------

class RLEC:
    def __init__(self, osnick=None, version=None, build=None, internal=False):
        self.rlec_view_root = None

        here = os.path.dirname(paella.current_filepath())
        self.view = paella.relpath(here, '../../..')
        self.viewname = os.path.basename(self.view)

        if self.rlec_view_root is None:
            self.rlec_view_root = paella.relpath(self.view, '..')

        self.internal_dir = '/opt/view/arlecchino/rlec/internal'
        self.rlec_dir = f"{self.view}/rlec"
        self._fix_rlec_dir()

        self._determine_docker_image(osnick=osnick, version=version, build=build, internal=internal)

        self.debug = os.getenv('BB', '') == '1'
        self.slow = os.getenv('SLOW', '') == '1'
        self.verbose = os.getenv('SHOW', '') == '1' or os.getenv('VERBOSE', '') == '1' or os.getenv('V', '') == '1'
        
        debug_file = f"{self.rlec_dir}/DEBUG"
        if self.debug:
            with open(debug_file, 'w'):
                pass
        else:
            try:
                os.unlink(debug_file)
            except:
                pass

    def _determine_docker_image(self, osnick=None, version=None, build=None, internal=False):
        if os.path.exists(f"{self.rlec_dir}/IMAGE"):
            docker_spec_f = json.loads(paella.fread(f"{self.rlec_dir}/IMAGE"))
        else:
            docker_spec_f = None

        image_stem = 'redislabs/redis-internal' if internal else 'redislabs/redis'
        if osnick is None and version is None and docker_spec_f is not None:
            docker_spec = docker_spec_f
            osnick = docker_spec["osnick"]
            version = docker_spec["version"]
            build = docker_spec["build"]
        else:
            if osnick is None:
                osnick = 'bionic'
            if version is None:
                version = RLEC_LATEST_VERSION if not internal else '100.0.0'
            if build is None:
                if internal:
                    if version == '100.0.0':
                        build = RLEC_INTERNAL_MASTER_BUILD
                else:
                    if version == RLEC_LATEST_VERSION:
                        build = RLEC_LATEST_BUILD
            if build is None:
                raise RuntimeError("Cannot determine build number")

            try:
                rlec_os = RLEC_OS[osnick]
            except:
                raise RuntimeError(f"Incompatible OS specified: {osnick}")

            docker_spec = { "image": f"{image_stem}:{version}-{build}.{rlec_os}",
                             "osnick": osnick,
                             "version": version,
                             "build": build }

        # if docker_image_f is None or docker_image != docker_image_f:
        #    paella.fwrite(f"{self.rlec_dir}/IMAGE", docker_image)
        self.docker_spec = docker_spec
        self.docker_image = docker_spec["image"]
        self.cnm_version = f"{version}-{build}"

        try:
            paella.sh(f"docker image inspect {self.docker_image}-fixed &> /dev/null")
            self.base_docker_image = self.docker_image
            self.docker_image += "-fixed"
            self.docker_image_fixed = True
        except:
            self.docker_image_fixed = False
        

    def _write_docker_image(self):
        docker_spec_f = None
        if os.path.exists(f"{self.rlec_dir}/IMAGE"):
            docker_spec_f = paella.fread(f"{self.rlec_dir}/IMAGE")

        if docker_spec_f is None or self.docker_spec != docker_spec_f:
            paella.fwrite(f"{self.rlec_dir}/IMAGE", json.dumps(self.docker_spec))

    def _fix_rlec_dir(self):
        d = os.path.join(self.view, "rlec")
        if not os.path.isdir(d):
            paella.mkdir_p(f"{d}")
            sh(f"sudo chmod 777 {d}")
            sh(f"sudo chmod g+s {d}")
            sh(f"touch {d}/.arlecchino")
            print(f"Control directory {d} created.")
            print("Note that redis-modules.yml needs to be created for loading modules.")
        elif not os.path.exists(f"{d}/.arlecchino"):
            sh(f"sudo chmod -R 777 {d}")
            sh(f"sudo chmod g+s {d}")

    #------------------------------------------------------------------------------------------

    def cid(self, node_num=1):
        k = node_num - 1
        file = f"{self.rlec_dir}/RLEC" + ("" if k == 0 else f".{k}")
        return paella.fread(file).strip()

    def no_internet(self):
        return os.path.exists(f"{self.rlec_dir}/NO_INTERNET")

    def is_running(self):
        return os.path.isfile(self.view + "/rlec/RLEC")

    def cluster(self):
        if self.is_running():
            cluster = Cluster(rlec=self)
        else:
            cluster = None
        return cluster

    def main_node(self):
        return Node(rlec=self)

    def node_log(self, num):
        return f"{self.rlec_dir}/out.{num}"

    def log(self, text, num=1, new=False):
        paella.fwrite(f"{self.node_log(num)}", f"{text}\n", mode="w" if new else "a+")
        if self.verbose:
            print(text)

    def fetch_logs(self):
        Cluster(rlec=self).fetch_logs()

    #------------------------------------------------------------------------------------------

    def create_cluster(self, dbname='', shards=1, no_modules=False, no_internet=False,
                       no_patch=False, no_bootstrap=False, keep=False, refix=False):
        self._write_docker_image()
        if no_internet:
            paella.fwrite(f"{self.rlec_dir}/NO_INTERNET", "")
        else:
            try:
                os.unlink(f"{self.rlec_dir}/NO_INTERNET")
            except:
                pass
        return Cluster.create(dbname=dbname, shards=1, no_modules=no_modules, no_patch=no_patch,
                              no_bootstrap=no_bootstrap, keep=keep, refix=refix, rlec=self)

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

    def create_db(self, name='db1', shards=3, memory='1g', sparse=False, replication=False, flash=None):
        cluster = self.cluster()
        if cluster is None:
            return
        cluster.create_db(name=name, shards=shards, memory=memory, sparse=sparse, replication=replication, flash=flash)

    #------------------------------------------------------------------------------------------

    def exec(self, cmd, uid=None, cid=None, num=None, to_log=True, to_con=False, vars={}, retout=False, debug=False):
        def write_log(out):
            if not num is None:
                self.log(out, num=num)

        if not uid is None:
            uid_arg = f"-u {uid}"
        else:
            uid_arg = ""
        #if to_con == True:
        #    to_con = to_log != True and not retout
        output = ""
        try:
            if num is None:
                num = 1
            if cid is None:
                cid = self.cid(node_num=num)
            # if debug is not None and debug or debug is None and os.getenv('BB', '0') == '1':
            if debug != False and os.getenv('BB', '0') == '1':
                to_log = False
                to_con = True
                vars['BB'] = '1'
                if '.py' not in cmd:
                    cmd = "bashdb " + cmd
            else:
                vars['BB'] = ''
            if self.verbose:
                vars['VERBOSE'] = '1'
            env_vars = " ".join([f'{n}="{str(v)}"' for n, v in vars.items()])

            cmd = f"docker exec {uid_arg} -it {cid} bash -c '{env_vars} {cmd}'"
            if self.verbose:
                print(f"Executing: {cmd}")
            if to_log or retout:
                output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, encoding="utf-8")
                if to_con or self.verbose:
                    print(output)
                if to_log:
                    write_log(output)
            else:
                subprocess.check_call(cmd, shell=True)
            if retout:
                return 0, output
            else:
                return 0
        except subprocess.CalledProcessError as x:
            BB()
            if to_log:
                write_log(x.output)
            if retout:
                return x.returncode, x.output
            else:
                return x.returncode

    def iexec(self, cmd, uid=None, cid=None, num=None, to_log=True, to_con=False, vars={}, retout=False, debug=False):
        # if (debug or os.getenv('BB', '0') == '1') and '.py' in cmd:
        #     cmd = f"/opt/redislabs/bin/python -O -m pudb {self.internal_dir}/{cmd}"
        # else:
        #     cmd = f"{self.internal_dir}/{cmd}"
        cmd = f"{self.internal_dir}/{cmd}"
        return self.exec(cmd, uid=uid, cid=cid, num=num, to_log=to_log, to_con=to_con,
                         vars=vars, retout=retout, debug=debug)

#----------------------------------------------------------------------------------------------

class Cluster(object):
    def __init__(self, rlec=None):
        if rlec is not None:
            self.rlec = rlec
        else:
            self.rlec = global_rlec()

    @ctor
    def create(self, dbname='', shards=1, no_modules=False, no_patch=False, no_bootstrap=False,
               keep=False, refix=False, rlec=None):
        if rlec is not None:
            self.rlec = rlec
        else:
            self.rlec = global_rlec()
        try:
            if rlec.is_running():
                print("RLEC cluster already running.")
                raise RuntimeError("RLEC cluster already running.")

            node = Node.create(no_patch=no_patch, refix=refix, rlec=rlec)

            # if not no_modules:
            #     print("Installing modules...")
            #     self.install_modules()
            #     print("Done.")
            # else:
            #     try:
            #         os.unlink(f"{rlec.view}/rlec/modules.json")
            #     except:
            #         pass

            if no_bootstrap:
                print("One node created (non-bootstrapped state).")
                return

            vars = {'NODE_NUM': node.num}
            # if debug:
            #     vars['BB'] = '1'
            if rlec.iexec("create-cluster.py", num=1, uid=0, vars=vars, to_log=True, to_con=True) != 0:
                raise RuntimeError("failed to create cluster")

            print("Cluster created.")

            if sh(f'{READIES}/bin/isec2') == 'no':
                dhost = DockerHost().host
            else:
                dhost = sh(f'{READIES}/bin/mainip')
            print(f"Can be managed via https://{dhost}:8443 [username: a@a.com, password: a]\n")
        except Exception as x:
            try:
                if not keep:
                    rlec.stop_cluster()
            except:
                pass
            print(f"Error creating RLEC cluster: {x}")
            raise RuntimeError(f"Error creating RLEC cluster: {x}")

    #------------------------------------------------------------------------------------------

    def node_numbers(self):
        return [int(f.split('.')[-1]) + 1 for f in glob(f"{self.rlec.view}/rlec/RLEC.*")]

    def last_node_num(self):
        nums = self.node_numbers()
        return max(nums) if nums != [] else 1

    #------------------------------------------------------------------------------------------

    def install_modules(self):
        if self.rlec.iexec("deploy-modules", num=1, to_log=True, to_con=True) != 0:
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
        print(f"Node stopped.")

    def nodes_info_by_ip(self, ip=None):
        rlec = self.rlec
        rc, info = rlec.iexec("info.py nodes-by-ip", to_log=False, to_con=False, retout=True)
        if rc != 0:
            raise RuntimeError("failed to get node info")
        info = json.loads(info)
        if ip is None:
            return info
        return info[ip] if ip in info else None

    def add_node(self, num=1, no_patch=False, no_join=False):
        rlec = self.rlec
        node = Node.create(num=num, no_patch=no_patch, rlec=rlec)
        if not no_join:
            self.join_node(node=node)

    def add_nodes(self, node_numbers, no_patch=False, no_join=False):
        if len(node_numbers) < 1:
            node_numbers = [self.last_node_num() + 1]
        xmap(lambda num: self.add_node(num=num, no_patch=no_patch, no_join=True), node_numbers)
        if not no_join:
            print("Joining nodes...")
            for num in node_numbers:
                self.join_node(num=num)
            print("Nodes joined cluster.")

    def join_node(self, num=None, node=None):
        if node is None:
            node = Node(num=num, rlec=self.rlec)
        rlec = self.rlec
        cluster_ip = rlec.main_node().ip()
        if rlec.iexec(f"join-cluster.py {cluster_ip}", num=num, uid=0, cid=node.cid, to_log=True, to_con=True, debug=True) != 0:
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

    def create_db(self, name='db1', shards=3, memory='1g', sparse=False, replication=False, flash=None):
        try:
            rlec = self.rlec
            sparse_arg = "--sparse" if sparse else ""
            repl_arg = "--replication" if replication else ""
            flash_arg = f"--flash {flash}" if flash is not None else ""
            # vars = {'BB': '1'}
            vars = {}
            if rlec.iexec(f"create-db.py --name={name} --shards={shards} --memory={memory} {sparse_arg} {repl_arg} {flash_arg}",
                          num=1, vars=vars, to_log=True, to_con=True) == 0:
                rlec.iexec("rediscli-info.py", num=1, uid=0, to_log=True, to_con=False)
            # print(f"Done.")
        except Exception as x:
            raise RuntimeError(f"Cannot create database: {str(x)}")

    def drop_db(slef, name="db1"):
        pass
        #try:
        #    rlec.iexec(f"drop-db.py --name={name}", num=1, to_log=True, to_con=True) == 0:
        #except Exception as x:
        #    raise RuntimeError(f"Cannot drop database: {str(x)}")

    def fetch_logs(self):
        Node(num=1).fetch_logs()
        for node_num in self.node_numbers():
            node = Node(num=node_num)
            node.fetch_logs()

#----------------------------------------------------------------------------------------------

class Node:
    def __init__(self, num=1, cid=None, rlec=None):
        if rlec is not None:
            self.rlec = rlec
        else:
            self.rlec = global_rlec()
        self.num = num
        if not cid is None:
            self.cid = cid
        else:
            self.cid = self.rlec.cid(num)
        self.cid_file = f"{self.rlec.view}/rlec/RLEC" + ("" if num == 1 else f".{num-1}")

    @ctor
    def create(self, num=1, no_patch=False, refix=False, rlec=None):
        if rlec is not None:
            self.rlec = rlec
        else:
            self.rlec = global_rlec()
            rlec = self.rlec
        cid = None
        try:
            if num > 1 and not rlec.is_running():
                print("RLEC cluster not running.")
                return False

            no_inet = "--network no-internet" if rlec.no_internet() else ""
            vol = f"-v {rlec.rlec_view_root}:/v"

            k = num - 1
            ports = f"-p {8443+k}:8443 -p {9443+k}:9443 -p {12000+k}:12000"

            rlec.log(f"Creating from {rlec.docker_image}", new=True)
            debug_opt = "--privileged --ulimit core=-1 --security-opt seccomp=unconfined"
            run_cmd = f"docker run -d {debug_opt} --cap-add sys_resource {no_inet} {ports} {vol} {rlec.docker_image}"
            if rlec.verbose:
                rlec.log(run_cmd)
            cid = sh(run_cmd)
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

            if num == 1:
                print(f"Preparing node {num}...")
                if refix and rlec.docker_image_fixed:
                    paella.sh(f"docker rmi {rlec.docker_image}")
                    rlec.docker_image = rlec.base_docker_image
                    rlec.docker_image_fixed = False
                if not rlec.docker_image_fixed:
                    rlec.exec(f"/v/{rlec.viewname}/arlecchino/rlec/internal/rlec-fixes", num=num, uid=0,
                              cid=cid, vars=newdict(vars, {'PROLOG': '1'}), debug=False)
                    rlec.exec(f"/v/{rlec.viewname}/arlecchino/rlec/internal/rlec-fixes", num=num, uid=0, cid=cid, vars=vars)
                    paella.sh(f"docker commit {cid} {rlec.docker_image}-fixed")
                    rlec.docker_image_fixed = True

            print(f"Node {num} created.")

            self.num = num
            self.cid = cid
        except:
            if not cid is None:
                subprocess.check_output(f"docker stop {cid}", shell=True, stderr=subprocess.STDOUT)
                subprocess.check_output(f"docker rm {cid}", shell=True, stderr=subprocess.STDOUT)
            print("Error creating RLEC node")
            raise RuntimeError("Error creating RLEC node")

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
        self.rlec.exec(f"cp /var/opt/redislabs/log/cnm_http.log /opt/view/rlec/cnm_http.log.{self.num}", num=self.num, to_log=False)
        self.rlec.exec(f"cp /var/opt/redislabs/log/cnm_exec.log /opt/view/rlec/cnm_exec.log.{self.num}", num=self.num, to_log=False)
        self.rlec.exec(f"cp /var/opt/redislabs/log/resource_mgr.log /opt/view/rlec/resource_mgr.log.{self.num}", num=self.num, to_log=False)

