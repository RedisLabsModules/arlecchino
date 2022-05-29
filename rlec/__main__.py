
from .common import *
from .commands import main

if __name__ == '__main__':
    if len(sys.argv) == 1:
        main(['--help'], prog_name="rlec")
    else:
        main(prog_name="rlec")
