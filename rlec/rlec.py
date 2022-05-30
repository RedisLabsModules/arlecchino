
from .common import *
from . import cfg
from .cluster import Cluster
from .node import Node

g_rlec = None

#----------------------------------------------------------------------------------------------

def global_rlec(rlec=None):
    global g_rlec
    if rlec is not None:
        g_rlec = rlec
    elif g_rlec is None:
        g_rlec = RLEC()
    return g_rlec

#----------------------------------------------------------------------------------------------

class RLEC:
    def __init__(self, osnick=None, version=None, build=None, internal=False):
        self.rlec_view_root = None

        here = os.path.dirname(paella.current_filepath())
        self.view = paella.relpath(here, '../..')
        self.viewname = os.path.basename(self.view)

        if self.rlec_view_root is None:
            self.rlec_view_root = paella.relpath(self.view, '..')

        self.internal_dir = '/opt/view/arlecchino/rlec/internal'
        self.rlec_dir = f"{self.view}/rlec"
        self._fix_rlec_dir()

        self.debug = ENV['BB'] == '1'
        self.slow = ENV['SLOW'] == '1'
        self.verbose = ENV['SHOW'] == '1' or ENV['VERBOSE'] == '1' or ENV['V'] == '1'

        self._determine_docker_image(osnick=osnick, version=version, build=build, internal=internal)

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
        # if os.path.exists(f"{self.rlec_dir}/IMAGE"):
        try:
            docker_spec_f = json.loads(paella.fread(f"{self.rlec_dir}/IMAGE"))
        except:
            docker_spec_f = None

        if osnick is None and version is None and docker_spec_f is not None:
            image_stem = 'redislabs/redis-internal' if internal else 'redislabs/redis'
            docker_spec = docker_spec_f
            osnick = docker_spec["osnick"]
            version = docker_spec["version"]
            build = docker_spec["build"]
        else:
            ver_build = ''
            if osnick is None:
                osnick = 'bionic'
            if version is None:
                version = RLEC_LATEST_INT_VERSION if internal else RLEC_LATEST_VERSION
            elif version == 'master':
                version = RLEC_INT_BUILDS[version]['version']
                internal = True
            else:
                fullver = version
                try:
                    version, ver_build = fullver.split('-')
                except:
                    ver_build = ''
            if build is None or build == '':
                if ver_build != '':
                    build = ver_build
                else:
                    try:
                        if internal:
                            build = RLEC_INT_BUILDS[version]['build']
                        else:
                            build = RLEC_BUILDS[version]['build']
                    except:
                        pass
                    if build == '':
                        raise Error(f"cannot determine build number for version={fullver}")
            elif ver_build != '' and build != ver_build:
                raise Error(f"conflicting build specs: version={fullver} build={build}")

            try:
                rlec_os = RLEC_OS[osnick]
            except:
                raise Error(f"incompatible OS specified: {osnick}")

            image_stem = 'redislabs/redis-internal' if internal else 'redislabs/redis'
            docker_spec = { "image": f"{image_stem}:{version}-{build}.{rlec_os}",
                             "osnick": osnick,
                             "version": version,
                             "build": build }

        # if docker_image_f is None or docker_image != docker_image_f:
        #    paella.fwrite(f"{self.rlec_dir}/IMAGE", docker_image)
        self.docker_spec = docker_spec
        self.docker_image = docker_spec["image"]
        self.cnm_version = f"{version}-{build}"

        self.fix_name = 'debug' if self.debug else 'fixed'
        try:
            paella.sh(f"docker image inspect {self.docker_image}-{self.fix_name} &> /dev/null")
            self.base_docker_image = self.docker_image
            self.docker_image += f"-{self.fix_name}"
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

    def unfix_docker_image(self):
        if not self.docker_image_fixed:
            return
        paella.sh(f"docker rmi -f {self.base_docker_image}-fixed")
        paella.sh(f"docker rmi -f {self.base_docker_image}-debug")
        self.docker_image = self.base_docker_image
        self.docker_image_fixed = False

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
        if refix:
            print(f"Using {self.base_docker_image}")
        else:
            print(f"Using {self.docker_image}")
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

    # excute command inside a container
    def exec(self, cmd, uid=None, cid=None, num=None, to_log=True, to_con=False, vars={}, retout=False, debug=None):
        def write_log(out):
            if not num is None:
                self.log(out, num=num)

        if debug is None and cfg.debug is not None:
            debug = cfg.debug

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
            if debug == True and os.getenv('BB', '0') == '1':
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

    # execute an internal script
    def iexec(self, cmd, uid=None, cid=None, num=None, to_log=True, to_con=False, vars={}, retout=False, debug=None):
        # if (debug or os.getenv('BB', '0') == '1') and '.py' in cmd:
        #     cmd = f"/opt/redislabs/bin/python -O -m pudb {self.internal_dir}/{cmd}"
        # else:
        #     cmd = f"{self.internal_dir}/{cmd}"
        cmd = f"{self.internal_dir}/{cmd}"
        return self.exec(cmd, uid=uid, cid=cid, num=num, to_log=to_log, to_con=to_con,
                         vars=vars, retout=retout, debug=debug)
