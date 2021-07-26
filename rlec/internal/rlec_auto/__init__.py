
import yaml

import warnings
import contextlib

import requests
from urllib3.exceptions import InsecureRequestWarning

from .info import *

#----------------------------------------------------------------------------------------------

def fread(fname):
    with open(fname, 'r') as file:
        return file.read()

def fwrite(fname, str):
    with open(fname, "w") as file:
        file.write(str)

def yaml_load(fname):
    with open(fname, "r") as file:
        return yaml.load(file, Loader=yaml.FullLoader)

#----------------------------------------------------------------------------------------------

old_merge_environment_settings = requests.Session.merge_environment_settings

@contextlib.contextmanager
def no_ssl_verification():
    opened_adapters = set()

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        # Verification happens only once per connection so we need to close
        # all the opened adapters once we're done. Otherwise, the effects of
        # verify=False persist beyond the end of this context manager.
        opened_adapters.add(self.get_adapter(url))

        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings['verify'] = False

        return settings

    requests.Session.merge_environment_settings = merge_environment_settings

    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', InsecureRequestWarning)
            yield
    finally:
        requests.Session.merge_environment_settings = old_merge_environment_settings
        for adapter in opened_adapters:
            try:
                adapter.close()
            except:
                pass
