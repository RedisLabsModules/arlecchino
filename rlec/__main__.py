#!/usr/bin/env python3

import os
import sys
import collections
import click
from textwrap import dedent
import time
import datetime
from rlec_docker import *

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
READIES = os.path.join(ROOT, "readies")
sys.path.insert(0, READIES)
import paella

VERSION = '1.0.0'

#----------------------------------------------------------------------------------------------

T0 = time.monotonic()

def report_elapsed():
    print(f"Elapsed: {datetime.timedelta(seconds=time.monotonic() - T0)}")

#----------------------------------------------------------------------------------------------

class Group1(click.Group):
    def __init__(self, name=None, commands=None, **attrs):
        super(Group1, self).__init__(name, commands, **attrs)
        self.commands = commands or collections.OrderedDict()

    @staticmethod
    def header():
        return r'''
             @-.
           _  )\\  _
          / \/ | \/ \
         @/`|/\/\/|`\@    Arlecchino v{VERSION}
            /~~~~~\
           |  ^ ^  |      Redis Enterprise Cluster
           |   .   |      on Docker
           | (\_/) |
        .-"-\ \_/ /-"-.
       / .-. \___/ .-. \
      @/` /.-.   .-.\ `\@
         @`   \ /   `@
               @

'''.format(VERSION=VERSION)

    @staticmethod
    def footer():
        return r'''

Variables:
RLEC         Root of RLEC view (mandatory)
DOCKER_HOST  Host running Docker server (tcp://127.0.0.1:2375 if undefined)
'''

    def get_help(self, ctx):
        h = super().get_help(ctx)
        return Group1.header() + h + Group1.footer()

    def list_commands(self, ctx):
        return self.commands

#----------------------------------------------------------------------------------------------

class Command1(click.Command):
    @staticmethod
    def header():
        return Group1.header()

    @staticmethod
    def footer():
        return r'''

Input files:
rlec.yaml           Cluster creation parameters
redis-modules.yaml  Redis modules for installation

Output files:
RLEC      Docker ID of master node
db1.yaml  Database attributes

Variables:
RLEC         Root of RLEC view
DOCKER_HOST  Host running Docker server (tcp://127.0.0.1:2375 if undefined)

'''

    def get_help(self, ctx):
        h = super().get_help(ctx)
        return Command1.header() + h + Command1.footer()

#----------------------------------------------------------------------------------------------

@click.group(cls=Group1, name="rlec", invoke_without_command=True)
@click.option('--debug', is_flag=True, help='Invoke debugger')
@click.option('--verbose', is_flag=True, help='Show output of all commands')
@click.option('--version', is_flag=True, help='Show version')
def main(debug, verbose, version):
    if version:
        print(f"Arlecchino {VERSION}")
        exit(0)

#----------------------------------------------------------------------------------------------

@main.command(help='Start RLEC cluster', cls=Command1)
@click.option('-o', '--os', 'osnick', type=str, default=None, help='RLEC osnick')
@click.option('-v', '--version', type=str, default=None, help='RLEC version')
@click.option('-b', '--build', type=str, default=None, help='RLEC build')
@click.option('-i', '--internal', is_flag=True, default=None, help='Use RLEC internal builds')
@click.option('-n', '--nodes', type=int, default=1, help='Number of nodes')
@click.option('-s', '--shards', type=int, default=3, help='Number of shards')
@click.option('-d', '--name', type=str, default='db1', help='Database name')
@click.option('-m', '--memory', type=str, default='1g', help='Memory (RAM)')
@click.option('--sparse', is_flag=True, help="Use sparse shard placement")
@click.option('--replication', is_flag=True, help="Enable replication")
@click.option('-M', '--module', 'modules', type=str, multiple=True, help='Install module from redis-modules.yaml')
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
@click.option('--debug', is_flag=True, help='Enable debug mode')
def start(osnick, version, build, internal, nodes, shards, name, memory, sparse, replication, modules,
          no_bootstrap, no_patch, no_db, no_modules, no_internet,
          quick, keep, verbose, slow, debug):
    if verbose:
        ENV['VERBOSE'] = "1"
    rlec = RLEC(osnick=osnick, version=version, build=build, internal=internal)
    if rlec.is_running():
        print("RLEC docker already running.")
        exit(1)
    print(f"Using {rlec.docker_image}")
    BB()
    rlec.create_cluster(no_modules=True, no_internet=no_internet, no_patch=no_patch,
                        no_bootstrap=no_bootstrap, keep=keep, debug=debug)
    if not no_bootstrap:
        if nodes > 1:
            rlec.add_nodes(range(2, 2 + nodes - 1), no_patch=no_patch)
        if not no_modules:
            rlec.install_modules()
        if not no_db:
            BB()
            rlec.create_db(name=name, shards=shards, memory=memory, sparse=sparse, replication=replication)
    rlec.fetch_logs()  # TODO: call fetch_logs after each operation, internally
    report_elapsed()
    exit(0)

#----------------------------------------------------------------------------------------------

@main.command(help='Stop RLEC cluster', cls=Command1)
def stop():
    rlec = RLEC()
    if not rlec.is_running():
        print("RLEC docker not running.")
        exit(1)
    rlec.stop_cluster()
    report_elapsed()
    exit(0)

#----------------------------------------------------------------------------------------------

# supervisorctl status
@main.command(help='Show RLEC cluster status', cls=Command1)
@click.option('-a', '--admin', is_flag=True, help="Run rladmin status")
@click.option('-s', '--services', is_flag=True, help="Run supervisorctl status")
def status(admin):
    rlec = RLEC()
    if not rlec.is_running():
        print("RLEC docker is not running.")
        exit(1)
    if admin:
        node = rlec.main_node()
        os.system(f"docker exec -u 0 -it {node.cid} bash -c 'rladmin status'")
        exit(0)
    if admin:
        node = rlec.main_node()
        os.system(f"docker exec -u 0 -it {node.cid} bash -c 'supervisorctl status'")
        exit(0)
    print("RLEC docker is running.")
    exit(0)

#----------------------------------------------------------------------------------------------

@main.command(help='Run rladmin')
def admin(*args):
    rlec = RLEC()
    if not rlec.is_running():
        print("RLEC docker is not running.")
        exit(1)
    node = rlec.main_node()
    os.system(f"docker exec -u 0 -it {node.cid} bash -c rladmin")
    exit(0)

#----------------------------------------------------------------------------------------------

@main.command(name='sh', help='Invoke RLEC command or interactive shell', cls=Command1)
@click.option('-n', '--node', type=int, default=1, help='Node number')
# @click.option('-c', '--command', type=str, default=[], help='Command')
@click.argument('command', nargs=-1, type=str)
def shell(node, command):
    BB()
    command = list(command)
    rlec = RLEC()
    if not rlec.is_running():
        print("RLEC docker not running.")
        exit(1)
    node = Node(num=node)
    if command == []:
        init = r"""
            if [[ -f /opt/view/rlec/DEBUG && -z $(command -v mc) ]]; then
                apt-get -qq update
                apt-get -qq install -y mc htop tmux 2>&1 > /tmp/apt.log
                [[ $? != 0 ]] && cat /tmp/apt.log
            fi
            """
        paella.fwrite(os.path.join(rlec.view, 'rlec', f"sh-init.{node.num}"), dedent(init))
        rc = os.system(f"docker exec -u 0 -it {node.cid} bash --init-file /opt/view/rlec/sh-init.{node.num}")
    else:
        rc = rlec.exec(' '.join(command), num=node.num, to_log=False, to_con=True)
    exit(rc)

#----------------------------------------------------------------------------------------------

@main.command(help='Run tmux')
def tmux():
    click.echo("tmux...")

#----------------------------------------------------------------------------------------------

@main.command(help='Invoke redis-cli in RLEC', cls=Command1)
@click.option('-n', '--node', type=int, default=1, help='Node number')
@click.option('-d', '--db', type=int, default=1, help='DB number')
def cli(node, db):
    click.echo("cli...")

#----------------------------------------------------------------------------------------------

@main.command(help='Fetch RLEC logs', cls=Command1)
def logs():
    rlec = RLEC()
    if not rlec.is_running():
        print("RLEC docker not running.")
        exit(1)
    rlec.fetch_logs()
    exit(0)

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
def add_node(osnick, version, build, internal, memory, join, no_join, patch, verbose, slow, reshard, node_nums):
    rlec = RLEC(osnick=osnick, version=version, build=build, internal=internal)
    if not rlec.is_running():
        print("RLEC docker is not running.")
        exit(1)
    if join:
        for num in node_nums:
            rlec.join_node(num=num)
    else:
        if len(node_nums) > 0:
            for num in node_nums:
                rlec.add_node(num=num, no_patch=not patch, no_join=no_join)
        else:
            # this will add a node with the next free number
            rlec.add_nodes(numbers=[], no_patch=not patch, no_join=no_join)
    rlec.fetch_logs()
    exit(0)

#----------------------------------------------------------------------------------------------

@main.command(name="node-", help='Remove RLEC node', cls=Command1)
def rm_node():
    click.echo("remove node...")

#----------------------------------------------------------------------------------------------

@main.command(help='Create a database', cls=Command1)
@click.option('-n', '--name', type=str, default='db1', help='Name of database')
@click.option('-m', '--memory', type=str, default='1g', help='Amount of RAM (default: 1g/1024m)')
@click.option('-s', '--shards', type=int, default=1, help='Number of shards')
@click.option('-f', '--filename', type=str, default='db1.yaml', help='Database parameters filename')
@click.option('--sparse', is_flag=True, help="Sparse shard placement")
@click.option('--replication', is_flag=True, help="Enable replication")
@click.option('--no-modules', is_flag=True, help="Do not install modules")
@click.option('--verbose', is_flag=True, help='Show output of all commands')
@click.option('--debug', is_flag=True, help='Debug internal RLEC script')
# def create_db(name, memory, shards, filename, sparse, replication, no_modules, verbose, *args, **kwargs):
def create_db(*args, **kwargs):
    BB()
    rlec = RLEC()
    if not rlec.is_running():
        print("RLEC docker not running.")
        exit(1)
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
    node = Node(num=1)
    return os.system(f"docker exec -u 0 -it {node.cid} bash -c \"{'BB=pudb' if debug else ''} /opt/view/arlecchino/rlec/internal/create-db.py {_args}\"")

#----------------------------------------------------------------------------------------------

@main.command(help='Drop a database')
def drop_db():
    click.echo("drop db...")

#----------------------------------------------------------------------------------------------

@main.command(help='Install modules')
def install_modules():
    click.echo("install modules...")

#----------------------------------------------------------------------------------------------

@main.command(help='Print help')
def help():
    with click.Context(main) as ctx:
        click.echo(main.get_help(ctx))

#----------------------------------------------------------------------------------------------

main.add_command(start)
main.add_command(stop)
main.add_command(status)
main.add_command(admin)
main.add_command(shell)
main.add_command(tmux)
main.add_command(cli)
main.add_command(logs)
main.add_command(add_node)
main.add_command(rm_node)
main.add_command(create_db)
main.add_command(drop_db)
main.add_command(install_modules)
main.add_command(help)

main()
