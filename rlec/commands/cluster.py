
from .common import *

from ..common import *
from ..rlec import RLEC, global_rlec
from ..cluster import Cluster
from ..node import Node

#----------------------------------------------------------------------------------------------

@main.command(help='Start RLEC cluster', cls=Command1)
@click.option('-o', '--os', 'osnick', type=str, default=None, help='RLEC osnick')
@click.option('-v', '--version', type=str, default=None, help='RLEC version')
@click.option('-b', '--build', type=str, default=None, help='RLEC build')
@click.option('-i', '--internal', is_flag=True, default=None, help='Use RLEC internal builds')
@click.option('-n', '--nodes', type=int, default=1, help='Number of nodes')
@click.option('-s', '--shards', type=int, default=3, help='Number of shards')
@click.option('-d', '--dbname', type=str, default='db1', help='Database name')
@click.option('-m', '--memory', type=str, default='1g', help='Memory (RAM)')
@click.option('--sparse', is_flag=True, help="Use sparse shard placement")
@click.option('--replication', is_flag=True, help="Enable replication")
@click.option('--flash', type=str, help="Enable Radis on Flash of given size")
@click.option('-M', '--module', 'modules', type=str, multiple=True, help='Install module from redis-modules.yml')
@click.option('--no-bootstrap', is_flag=True, help='Do no bootstrap')
@click.option('--no-patch', is_flag=True, help='Do not apply patches')
@click.option('--no-db', is_flag=True, help='Do not create database')
@click.option('--no-modules', is_flag=True, help='Do not load modules')
@click.option('--no-internet', is_flag=True, help='No internet access')
@click.option('--quick', is_flag=True, help='Skip package installation')
@click.option('-k', '--keep', is_flag=True, help='Do not remove failing nodes')
# @click.option('--show-platforms', is_flag=True, help='Show RLEC platforms')
@click.option('--verbose', is_flag=True, help='Show output of all commands')
@click.option('--slow', is_flag=True, help='Do not run in parallel')
@click.option('--refix', is_flag=True, help='Recreate fixed images')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def start(**kwargs):
    args = dict_to_nt('StartArgs', kwargs)
    BB()
    try:
        setup_env(args)
        rlec = global_rlec(RLEC(osnick=args.osnick, version=args.version, build=args.build, internal=args.internal))
        if rlec.is_running():
            print("RLEC docker already running.")
            exit(1)
        rlec.create_cluster(no_modules=True, no_internet=args.no_internet, no_patch=args.no_patch,
                            no_bootstrap=args.no_bootstrap, keep=args.keep, refix=args.refix)
        if not args.no_bootstrap:
            nodes = args.nodes
            if nodes > 1:
                rlec.add_nodes(range(2, 2 + nodes - 1), no_patch=args.no_patch)
            if not args.no_modules:
                rlec.install_modules()
            if not args.no_db:
                rlec.create_db(name=args.dbname, shards=args.shards, memory=args.memory, sparse=args.sparse, 
                               replication=args.replication, flash=args.flash)
        rlec.fetch_logs()  # TODO: call fetch_logs after each operation, internally
    except Error as x:
        eprint(f"Error: {x}")
    except Exception as x:
        eprint(f"Internal error: {x}")
        click.echo("")
        traceback.print_exc()
        click.echo("")
    report_elapsed()
    exit(0)

#----------------------------------------------------------------------------------------------

@main.command(help='Stop RLEC cluster', cls=Command1)
def stop(*kwargs):
    args = dict_to_nt('StopArgs', kwargs)
    BB()
    rlec = global_rlec()
    if not rlec.is_running():
        print("RLEC docker not running.")
        exit(1)
    rlec.stop_cluster()
    report_elapsed()
    exit(0)
