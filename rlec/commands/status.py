from .common import *

#from ..common import *
from ..rlec import global_rlec
from ..node import Node

#----------------------------------------------------------------------------------------------

# supervisorctl status
@main.command(help='Show RLEC cluster status', cls=Command1)
@click.option('-a', '--admin', is_flag=True, help="Run rladmin status")
@click.option('-s', '--services', is_flag=True, help="Run supervisorctl status")
def status(**kwargs):
    args = dict_to_nt('StatusArgs', kwargs)
    BB()
    rlec = global_rlec()
    if not rlec.is_running():
        print("RLEC docker is not running.")
        exit(1)
    if args.admin:
        node = rlec.main_node()
        os.system(f"docker exec -u 0 -it {node.cid} bash -c 'rladmin status'")
        exit(0)
    if args.services:
        node = rlec.main_node()
        os.system(f"docker exec -u 0 -it {node.cid} bash -c 'supervisorctl status'")
        exit(0)
    print("RLEC docker is running.")
    exit(0)
