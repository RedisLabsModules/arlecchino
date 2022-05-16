import click
import collections
from collections import namedtuple

from ..env import *

COMMIT = sh("git rev-parse --short HEAD 2>/dev/null || echo '?'")
VERSION = '1.1.0'

#----------------------------------------------------------------------------------------------

def dict_to_nt(name, d):
    if not d:
         return namedtuple(name, {})()
    return namedtuple(name, d.keys())(**d)

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
         @/`|/\/\/|`\@    Arlecchino v{VERSION}-{COMMIT}
            /~~~~~\
           |  ^ ^  |      Redis Enterprise Cluster
           |   .   |      on Docker
           | (\_/) |
        .-"-\ \_/ /-"-.
       / .-. \___/ .-. \
      @/` /.-.   .-.\ `\@
         @`   \ /   `@
               @

'''.format(VERSION=VERSION, COMMIT=COMMIT)

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
rlec.yaml          Cluster creation parameters
redis-modules.yml  Redis modules for installation

Output files:
RLEC      Docker ID of master node
db1.yml   Database attributes

Variables:
RLEC          Root of RLEC view
DOCKER_HOST   Host running Docker server (tcp://127.0.0.1:2375 if undefined)

'''

    def get_help(self, ctx):
        h = super().get_help(ctx)
        return Command1.header() + h + Command1.footer()

#----------------------------------------------------------------------------------------------

@click.group(cls=Group1, name="rlec", invoke_without_command=True)
@click.option('--version', is_flag=True, help='Show version')
@click.option('--where', is_flag=True, help='Show where Arlecchino view is located')
@click.option('--verbose', is_flag=True, help='Show output of all commands')
@click.option('--debug', is_flag=True, help='Enable debugging')
@click.option('--slow', is_flag=True, help='Do not run in parallel')
@click.option('--update', is_flag=True, help='Check for updates')
def main(**args_):
    args = dict_to_nt('MainArgs', args_)
    if args.version:
        print(f"Arlecchino {VERSION}-{COMMIT}")
        exit(0)
    setup_env(args)

#----------------------------------------------------------------------------------------------

@main.command(help='Print help')
def help():
    with click.Context(main) as ctx:
        click.echo(main.get_help(ctx))
