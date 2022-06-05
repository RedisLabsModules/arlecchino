from .common import *
from ..common import *
from ..rlec import RLEC, global_rlec

#----------------------------------------------------------------------------------------------

@main.command(help='Create a database', cls=Command1)
@click.option('-n', '--name', type=str, default='db', help='Name of database')
@click.option('-m', '--memory', type=str, default='1g', help='Amount of RAM (default: 1g/1024m)')
@click.option('-s', '--shards', type=int, default=1, help='Number of shards')
@click.option('-f', '--filename', type=str, default='db.yml', help='Database parameters filename')
@click.option('--sparse', is_flag=True, help="Sparse shard placement")
@click.option('--replication', is_flag=True, help="Enable replication")
@click.option('--flash', type=str, help="Enable Radis on Flash of given size")
@click.option('--modules', type=str, help='File specifying modules with arguments for loading')
@click.option('--no-modules', is_flag=True, help="Do not install modules")
@click.option('--verbose', is_flag=True, help='Show output of all commands')
@click.option('--debug', is_flag=True, help='Debug internal RLEC script')
@click.option('--slow', is_flag=True, help='Do not run in parallel')
def create_db(*args, **kwargs):
    try:
        args = dict_to_nt('CreateDBArgs', kwargs)
        BB()
        rlec = global_rlec()
        if not rlec.is_running():
            print("RLEC docker not running.")
            exit(1)
        setup_env(args)
        rlec.create_db(name=args.name, shards=args.shards, memory=args.memory, sparse=args.sparse, 
                       replication=args.replication, flash=args.flash, modules_file = args.modules,
                       no_modules=args.no_modules)
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

@main.command(help='Drop a database')
def drop_db():
    click.echo("drop db...")
