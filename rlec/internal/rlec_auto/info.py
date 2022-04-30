#!/bin/sh
''''[ ! -z $VIRTUAL_ENV ] && exec /opt/redislabs/bin/python -O -u -- "$0" ${1+"$@"}; command -v /opt/redislabs/bin/python3 > /dev/null && exec /opt/redislabs/bin/python3 -O -u -- "$0" ${1+"$@"}; exec /opt/redislabs/bin/python2 -O -u -- "$0" ${1+"$@"} # '''

try:
    from cnm import CCS
    from cnm.cli import rladmin
except:
    import sys
    sys.path.insert(0, "/opt/redislabs/lib/cnm") 
    sys.path.insert(0, "/opt/redislabs/lib/cnm/python") 
    import CCS
    from cli import rladmin
import json

class Info:
    def __init__(self):
        self.ccs = CCS.Context()
        self.cluster_status = rladmin.ClusterStatus(self.ccs)

    def nodes(self):
        nodes = []
        master_uid = self.cluster_status.master_node.uid()
        for node in self.cluster_status.nodes.values():
            uid = node.uid()
            nodes.append({ 'id': uid, 
                           'ip': node.addr(), 
                           'status': node.status(), 
                           'alive': self.cluster_status.node_is_alive(uid), 
                           'master': uid == master_uid })
        return nodes

    def nodes_by_ip(self):
        nodes = {}
        for node in self.nodes():
            nodes[node["ip"]] = node
        return nodes

    def databases(self):
        pass
    
    def shards(self):
        pass
