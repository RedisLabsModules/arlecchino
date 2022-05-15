import os
import sys

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
READIES = os.path.join(ROOT, "readies")
sys.path.insert(0, READIES)
import paella

#----------------------------------------------------------------------------------------------

def setup_env(args):
    if args.verbose:
        ENV['VERBOSE'] = "1"
    if args.debug:
        # ENV['DEBUG'] = "1"
        ENV['BB'] = "1"
    if args.slow:
        ENV['SLOW'] = "1"
