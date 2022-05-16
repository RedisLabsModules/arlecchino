import os
import sys
import click

from .common import Group1, Command1, main, help
from .cluster import start, stop
from .node import add_node, rm_node
from .shell import shell, cli
from .status import status
from .db import create_db, drop_db

from ..common import *
from ..rlec import global_rlec

#----------------------------------------------------------------------------------------------

@main.command(help='Run rladmin')
def admin(**kwargs):
    rlec = global_rlec()
    if not rlec.is_running():
        print("RLEC docker is not running.")
        exit(1)
    node = rlec.main_node()
    os.system(f"docker exec -u 0 -it {node.cid} bash -c rladmin")
    exit(0)

#----------------------------------------------------------------------------------------------

@main.command(help='Run tmux')
def tmux():
    click.echo("tmux...")

#----------------------------------------------------------------------------------------------

@main.command(help='Fetch RLEC logs', cls=Command1)
def logs():
    rlec = global_rlec()
    if not rlec.is_running():
        print("RLEC docker not running.")
        exit(1)
    rlec.fetch_logs()
    exit(0)

#----------------------------------------------------------------------------------------------

@main.command(help='Install modules')
def install_modules():
    click.echo("install modules...")

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
