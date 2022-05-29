from .common import *

#----------------------------------------------------------------------------------------------

@main.command(help='Create a database', cls=Command1)
@click.option('-n', '--name', type=str, default='db1', help='Name of database')
@click.option('-m', '--memory', type=str, default='1g', help='Amount of RAM (default: 1g/1024m)')
@click.option('-s', '--shards', type=int, default=1, help='Number of shards')
@click.option('-f', '--filename', type=str, default='db1.yml', help='Database parameters filename')
@click.option('--sparse', is_flag=True, help="Sparse shard placement")
@click.option('--replication', is_flag=True, help="Enable replication")
@click.option('--no-modules', is_flag=True, help="Do not install modules")
@click.option('--verbose', is_flag=True, help='Show output of all commands')
@click.option('--debug', is_flag=True, help='Debug internal RLEC script')
@click.option('--slow', is_flag=True, help='Do not run in parallel')
# def create_db(name, memory, shards, filename, sparse, replication, no_modules, verbose, *args, **kwargs):
def create_db(*args, **kwargs):
    BB()
    _args = ''
    for k, v in kwargs.items():
        if k == 'debug':
            continue
        k = k.replace('_', '-')
        if type(v) == str:
            _args += f' --{k} "{v}"'
        elif type(v) == int:
            _args += f' --{k} {v}'
        elif type(v) == bool and v:
            _args += f' --{k}'
    #_args = f'--name "{name}" --memory {memory} --shards {shards} --filename {filename}'
    #_args += ' --sparse' if sparse else ''
    #_args += ' --replication' if replication else ''
    #_args += ' --no-modules' if no_modules else ''
    verbose = kwargs['verbose']
    debug = kwargs['debug']
    slow = kwargs['slow']
    rlec = global_rlec()
    if not rlec.is_running():
        print("RLEC docker not running.")
        exit(1)
    setup_env(verbose, debug, slow)
    node = Node(num=1)
    return os.system(f"docker exec -u 0 -it {node.cid} bash -c \"{'BB=pudb' if debug else ''} /opt/view/arlecchino/rlec/internal/create-db.py {_args}\"")

#----------------------------------------------------------------------------------------------

@main.command(help='Drop a database')
def drop_db():
    click.echo("drop db...")
