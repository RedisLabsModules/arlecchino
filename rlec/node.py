
from .common import *
from . import cfg
# from .rlec import RLEC
# from .cluster import Cluster

class Node:
    def __init__(self, num=1, cid=None, rlec=None):
        if rlec is not None:
            self.rlec = rlec
        else:
            from .rlec import global_rlec
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
            from .rlec import global_rlec
            self.rlec = global_rlec()
            rlec = self.rlec
        cid = None
        try:
            if num > 1 and not rlec.is_running():
                print("RLEC cluster not running.")
                return False

            if num == 1 and refix:
                rlec.unfix_docker_image()

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
                if not rlec.docker_image_fixed:
                    rlec.exec(f"/v/{rlec.viewname}/arlecchino/rlec/internal/rlec-fixes", num=num, uid=0,
                              cid=cid, vars=newdict(vars, {'PROLOG': '1'}), debug=False)
                    rlec.exec(f"/v/{rlec.viewname}/arlecchino/rlec/internal/rlec-fixes", num=num, uid=0, cid=cid, vars=vars)
                    paella.sh(f"docker commit {cid} {rlec.docker_image}-{rlec.fix_name}")
                    rlec.docker_image_fixed = True

            print(f"Node {num} created.")

            self.num = num
            self.cid = cid
        except:
            if not cid is None:
                subprocess.check_output(f"docker stop {cid}", shell=True, stderr=subprocess.STDOUT)
                subprocess.check_output(f"docker rm {cid}", shell=True, stderr=subprocess.STDOUT)
            print("Error creating RLEC node")
            raise Error("error creating RLEC node")

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
        self.rlec.exec(f"cp /var/opt/redislabs/log/cnm_http.log /opt/view/rlec/cnm_http.log.{self.num}", num=self.num, to_log=False, debug=False)
        self.rlec.exec(f"cp /var/opt/redislabs/log/cnm_exec.log /opt/view/rlec/cnm_exec.log.{self.num}", num=self.num, to_log=False, debug=False)
        self.rlec.exec(f"cp /var/opt/redislabs/log/resource_mgr.log /opt/view/rlec/resource_mgr.log.{self.num}", num=self.num, to_log=False, debug=False)
