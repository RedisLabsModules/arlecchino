from .common import *
from ..rlec import global_rlec

#----------------------------------------------------------------------------------------------

@main.command(name='sh', help='Invoke RLEC command or interactive shell', cls=Command1)
@click.option('-n', '--node', type=int, default=1, help='Node number')
# @click.option('-c', '--command', type=str, default=[], help='Command')
@click.argument('command', nargs=-1, type=str)
def shell(**kwargs):
    args = dict_to_nt('ShellArgs', kwargs)
    BB()
    command = list(args.command)
    rlec = global_rlec()
    if not rlec.is_running():
        print("RLEC docker not running.")
        exit(1)
    node = Node(num=args.node)
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

@main.command(help='Invoke redis-cli in RLEC', cls=Command1)
@click.option('-n', '--node', type=int, default=1, help='Node number')
@click.option('-d', '--db', type=int, default=1, help='DB number')
def cli(**kwargs):
    args = dict_to_nt('CliArgs', kwargs)
    BB()
    click.echo("cli...")
