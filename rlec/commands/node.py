from .common import *

#----------------------------------------------------------------------------------------------

@main.command(name="node+", help='Add RLEC node', cls=Command1)
@click.option('-o', '--os', 'osnick', type=str, default=None, help='RLEC osnick')
@click.option('-v', '--version', type=str, default=None, help='RLEC version')
@click.option('-b', '--build', type=str, default=None, help='RLEC build')
@click.option('-i', '--internal', is_flag=True, default=None, help='Use RLEC internal builds')
@click.option('-m', '--memory', type=str, default='1g', help='Memory (RAM)')
@click.option('--join', default=False, help='Join existing nodes')
@click.option('--no-join', default=False, help='Create node but don\'t join cluster')
@click.option('--patch / --no-patch', default=True, help='Do not apply patches')
@click.option('--verbose', is_flag=True, help='Show output of all commands')
@click.option('--slow', is_flag=True, help='Do not run in parallel')
@click.option('--reshard', is_flag=True, help='Reshard after adding nodes')
@click.argument('node-nums', type=int, nargs=-1)#, help='Node numbers')
def add_node(**kwargs):
    args = dict_to_nt('AddNodeArgs', kwargs)
    BB()
    rlec = global_rlec(RLEC(osnick=args.osnick, version=args.version, build=args.build, internal=args.internal))
    if not rlec.is_running():
        print("RLEC docker is not running.")
        exit(1)
    if args.join:
        for num in args.node_nums:
            rlec.join_node(num=num)
    else:
        if len(args.node_nums) > 0:
            for num in args.node_nums:
                rlec.add_node(num=num, no_patch=not args.patch, no_join=ars.no_join)
        else:
            # this will add a node with the next free number
            rlec.add_nodes(numbers=[], no_patch=not args.patch, no_join=args.no_join)
    rlec.fetch_logs()
    exit(0)

#----------------------------------------------------------------------------------------------

@main.command(name="node-", help='Remove RLEC node', cls=Command1)
def rm_node():
    args = dict_to_nt('RMNodeArgs', kwargs)
    BB()
    click.echo("remove node...")
