![](docs/arlecchino.webp) 

<img src="W:\rafi_3\arlecchino\docs\rlecchino.webp" alt="rlecchino" style="zoom:33%;" />

# Arlecchino

### So you want to run Redis Software with Redis Modules, eh?

## Why like this?

* You want to quickly setup a Redis Software (Enterprise) Cluster using Docker
* You need a quick edit-compile-test experience with a Redis module in a RS Cluster
* You'd like to automate RS Cluster-related scenarios (e.g., for automatic testing)

## What's needed?

* A machine with at least 16GB RAM (cloud machines will work fine)
* Python 3.6 or higher
* Docker installation that can operate with volumes (i.e., `docker run -v /v:/v ...`)
* Permissions to access [RedisLabs Dockerhub Internal Repo](https://hub.docker.com/repository/docker/redislabs/redis-internal/tags)
* A directory on your filesystem, designated as a **view directory**

## Fellas, I'm ready to get up and do my thing

First, let's create a **view directory**, which is simply a directory that will hold your cloned Git modules (and some more stuff we'll soon encounter), and actually act as a point of reference to the RS instances we'll be running.

We'll first see how to run a single node RS instance without modules, and then add more nodes and modules to the pan.

To prepare the view, execute the following from within the view directory:
```
source <(curl -Ls http://tiny.cc/rlec-docker)
```

This will also introduce several commands (as aliases), all starting with ''rlec-'' prefix, that will refer to our view, no matter from which directory they are invoked, as long as you run from the same shell instance.<a href="#note1" id="note1ref"><sup>1</sup></a>

Without delay, invoke the first one:
```
rlec-start
```

It will download a RS docker image and run it.

Let's look at the output:

```
Control directory /view1/rlec created.
Note that redis-modules.yaml needs to be created for loading modules.
Created docker 3b5c55b3ffc44e9dee82d2d881be8033b6744e088748ced934ba475f03dd50e1
Patching CNM...
Looking for custom CNM artifacts at /opt/view/modullaneous/rlec-docker/cnm-5.4.6-11/python
Found!
Syching the following CNM artifacts:
/v/rafi_2/modullaneous/rlec-docker/cnm-5.4.6-11/python/CCS.py -> /opt/redislabs/lib/cnm/CCS.py
/v/rafi_2/modullaneous/rlec-docker/cnm-5.4.6-11/python/http_services/cluster_api/module_handler.py -> /opt/redislabs/lib/cnm/http_services/cluster_api/module_handler.py
cnm_exec: stopped
cnm_exec: started
cnm_http: stopped
cnm_http: started
No modules specified.

Creating cluster...
Creating a new cluster... ok

Creating database...
Done.
```

## What just happened?

First, the control directory is announced. This is a directory to which RS writes useful information (such as Redis config files), and also a place for us to create configuration files to tweak its behavior.

Next, CNM patching takes place. More on that later.

After patching is done, modules are installed from their packages into the RS container.

Once modules are in place, a cluster is created, followed by a Redis database. That's it - we now can use Redis, which is available on it's default port: 6379.

Actually, we can approach RS in two ways:

* Using the ```rlec-cli``` command, which will invoke redis-cli (it has to be installed on our host for this to work).
* Using the ```rlec-sh``` command, which will SSH into the RS container, where we can examine logs and other RS internal matters. It is also possible to invoke redis-cli from within the container.

We can also examine the status of our RS instance with the ```rlec-status``` command, which simply report whether RS is running on not.

Finally, we can stop the RS container using ```rlec-stop```, which will stop the RS cluster  but keep the control directory in place, so we can create a new one with the same characteristics.

This is a good time to introduce the `rlec-help` command, which displays the following:
```
RLEC Docker operations.

rlec-start                Start cluster (node 1 & boostrap)
rlec-stop                 Stop cluster (stop all nodes)
rlec-status               Show cluster status (running/stopped)
rlec-sh                   Execute shell (or command) on a node
rlec-cli                  Execute redis-cli
rlec-add-node|rlec-node+  Start a node and add it to the cluster
rlec-rm-node|rlec-node-   Remove a node from cluster and terminate it
rlec-create-db            Create a database
rlec-drop-db              Drop a database
rlec-reinstall-modules    Reinstall Redis modules

Input files:
rlec.yaml           Cluster creation parameters
redis-modules.yaml  Redis modules for installation

Output files:
RLEC                Docker ID of master node
db1.yaml            Database attributes

Variables:
RLEC         Root of RLEC view
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

Looking at ```rlec-start``` output, it looks almost obvious.

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

We just need to connect RLTest to the RS container, and we're off to the races.

## Appendis: CNM

CNM is a Python modules that controls RS operation. One often needs to debug it to understand why CNM acts the way it does, or modify it in a way that suites our need. Since CNS is distributed in binary form within the RS docker image, we need to use some trickery to get (possibly modified) Python source code into the container.

## Redis logs within RS

TBD

## Location of modules within RS

TBD

## Footnotes

<a  id="note1" href="#note1ref"><sup>1</sup></a>
In order to enable rlec- commands from an other shell instance, invoke `source $viewdir/modullaneous/rlec-docker/aliases`, with $viewdir being the path of your view directory.