
from .common import *
from . import cfg
from .node import Node

#----------------------------------------------------------------------------------------------

class Cluster(object):
    def __init__(self, rlec=None):
        if rlec is not None:
            self.rlec = rlec
        else:
            from .rlec import global_rlec
            self.rlec = global_rlec()

    @ctor
    def create(self, dbname='', shards=1, no_modules=False, no_patch=False, no_bootstrap=False,
               keep=False, refix=False, rlec=None):
        if rlec is not None:
            self.rlec = rlec
        else:
            from .rlec import global_rlec
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
            BB()
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
        if rlec.iexec(f"join-cluster.py {cluster_ip}", num=num, uid=0, cid=node.cid, to_log=True, to_con=True) != 0:
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
