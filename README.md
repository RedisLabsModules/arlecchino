<img src="https://raw.githubusercontent.com/RedisLabsModules/arlecchino/master/docs/arlecchino.webp?token=ABZG4OYKG6TNR6ADZWMSYFLBFKMBQ" alt="logo" width="300"/>

# Arlecchino

### So you want to run Redis Enterprise with Redis Modules, eh?

## Why?

* Quickly setup a Redis Enterprise Cluster (RLEC) using Docker
* Quick edit-compile-test experience with a Redis module in a Redis Enterprise Cluster
* Run RLTest tests on a Redis Enterprise Cluster

## What's needed?

* A machine with at least 16GB RAM (cloud machines will work fine)
* Python 3.6 or higher
* Docker installation that can operate with volumes (i.e., `docker run -v /v:/v ...`)
* A directory on your filesystem, designated as a **view directory**
* Permissions to access [RedisLabs Dockerhub Internal Repo](https://hub.docker.com/repository/docker/redislabs/redis-internal/tags) (optional)

## Fellas, I'm ready to get up and do my thing

First, let's create a **view directory**, which is simply a directory that will hold your cloned Git repos of Redis Modules (and some more stuff we'll soon encounter), and actually act as a point of reference to the RLEC instances we'll be running.

We'll first see how to run a single node RLEC instance without modules, and then add more nodes and modules to the pan.

To prepare the view, execute the following from within the view directory (we're using `/view` for simplicity, but you can place it in your home directory, for instance):
```
mkdir /view
cd /view
source <(curl -Ls http://tiny.cc/arlecchino)
```

This will also introduce the `rlec` command which will allow us to operate the cluster.
Without delay, invoke the first one:

```
rlec start
```

It will download a RLEC docker image and run it.

Let's look at the output:

```
Control directory /view/rlec created.
Note that redis-modules.yaml needs to be created for loading modules.
Using redislabs/redis:6.0.20-97.bionic
Preparing node 1...
Node 1 created.
Cluster created.
Can be managed via https://3.249.58.234:8443 [username: a@a.com, password: a]
Elapsed: 0:01:09.440558
```

## What just happened?

First, the control directory is announced. This is a directory to which *arlecchino* writes file with useful information, and also a place for us to create configuration files.

If RLEC version information is not specified, *arlecchino* will select one and start its container.
Once the container is ready, Redis Modules are installed and a database is created.

That's it - we now can use RLEC, which is available on port: 12000:
```
redis-cli -p 12000
```

Actually, we can approach RS in two ways:

* Using the `rlec cli` command, which will invoke `redis-cli` (it has to be installed on our host for this to work).
* Using the `rlec sh` command, which will SSH into the RLEC container, where we can examine logs and other RS internal matters. It is also possible to invoke bdb-cli from within the container.

We can also examine the status of our RS instance with the `rlec status` command, which simply report whether RS is running on not. `rlec status -a` will invoke `rladmin` from within the container.

Finally, we can stop the RS container using `rlec stop`, which will stop the RLEC cluster but keeps the control directory in place, so we can create a new one with the same characteristics.

This is a good time to introduce the `rlec help` command, which displays the following:
```
             @-.
           _  )\\  _
          / \/ | \/ \
         @/`|/\/\/|`\@    Arlecchino v1.0.0
            /~~~~~\
           |  ^ ^  |      Redis Labs Enterprise Cluster
           |   .   |      on Docker
           | (\_/) |
        .-"-\ \_/ /-"-.
       / .-. \___/ .-. \
      @/` /.-.   .-.\ `\@
         @`   \ /   `@
               @

Usage:  [OPTIONS] COMMAND [ARGS]...

Options:
  --debug    Invoke debugger
  --verbose  Show output of all commands
  --version  Show version
  --help     Show this message and exit.

Commands:
  start            Start RLEC cluster
  stop             Stop RLEC cluster
  status           Show RLEC cluster status
  admin            Run rladmin
  sh               Invoke RLEC command or interactive shell
  tmux             Run tmux
  cli              Invoke redis-cli in RLEC
  logs             Fetch RLEC logs
  node+            Add RLEC node
  node-            Remove RLEC node
  create_db        Create a database
  drop_db          Drop a database
  install_modules  Install modules
  help             Print help

Variables:
DOCKER_HOST  Host running Docker server (localhost if undefined)
```

## Redis modules

We can now turn to loading modules into RS. We use YAML file named ```redis-modules.yaml``` to control which modules are installed and where to fetch them from:

```
redisearch:
    path: /opt/view/RedisSearch/redisearch-enterprise.zip
    module: yes
redisgraph:
    path: /opt/view/RedisGraph/redisgraph.zip
    module: yes
rejson:
    path: /opt/view/RedisJSON/rejson.zip
    module: yes
rebloom:
    path: /opt/view/RedisBloom/rebloom.zip
    module: yes
redisgears:
    path: /opt/view/RedisGears/bin/linux-x64-release/redisgears.Linux-x86_64.latest.zip
    module: yes
redisgears-deps:
    path: /opt/view/RedisGears/artifacts/release/redisgears-dependencies.Linux-x86_64.latest.tgz
    dest: /
    unzip: yes
redistimeseries:
    path: /opt/view/RedisTimeSeries/redistimeseries.zip
    module: yes
redisai:
    path: /opt/view/RedisAI/build/redisai.zip
    module: yes
redisai-deps:
    path: /opt/view/RedisAI/build/redisai-dependencies.tar.gz
    dest: /opt/redislabs/lib/modules/lib
    unzip: yes 
```

The ```redis-modules.yaml``` file resides in the RLEC control directory. We can copy a general template from ```modullaneous/rlec-mod-install/redis-modules-docker.yaml``` (relative to the view directory) and simply comment out modules we don't need. Actually, modules that will be missing during the RS container startup will be ignored, so we may just leave the template as it is.

Sharp-eyed readers will notice the ```/opt/view``` path in the YAML file. This is simply how the RS container sees the our host view directory (it is mapped as a volume).

So we can now put ```redis-modules.yaml``` in its place and repeat the creation process.

If an RS instance is still running, ```rlec-start``` will complain, so just use ```rlec-stop``` to stop the previous instance.

We'll use RedisAI module to demonstrate. We'll assume we cloned it into our view and built it.

The results of the build and packaging process are a RAMP file and (in case of RedisAI) a dependency tar file.

Looking at `rlec start` output, it looks almost obvious.

```
Created docker ce87e9fc3bbb4697e82be14f3b9886771a6df14ef6494a27f21e67e781a8ac4d
Patching CNM...
Looking for custom CNM artifacts at /opt/view/modullaneous/rlec-docker/cnm-5.4.6-11/python
Found!
Syching the following CNM artifacts:
/v/rafi_1/modullaneous/rlec-docker/cnm-5.4.6-11/python/CCS.py -> /opt/redislabs/lib/cnm/CCS.py
/v/rafi_1/modullaneous/rlec-docker/cnm-5.4.6-11/python/http_services/cluster_api/module_handler.py -> /opt/redislabs/lib/cnm/http_services/cluster_api/module_handler.py
cnm_exec: stopped
cnm_exec: started
cnm_http: stopped
cnm_http: started
Installing modules...
installing redisai...
installing redisai-deps...
Done.
Creating a new cluster... ok
Cluster created with the following modules: redisai redisai-deps 
Creating database...
Done.
```

That's it!

We just need to connect RLTest to the RLEC container, and we're off to the races.

## Appendix: Cluster creation in details
...

## Appendix: CNM and CNM patches

CNM is a Python modules that controls RLEC operation. One often needs to debug it to understand why CNM acts the way it does, or modify it in a way that suites our need. Since CNS is distributed in binary form within the RLEC docker image, we need to use some trickery to get (possibly modified) Python source code into the container.

## Appendix: Redis logs within RLEC

...

## Appendix: Location of modules within RLEC

...

## Footnotes
