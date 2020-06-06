Docker environment for SimpleMonitor
====================================

Caveat: I'm not a Docker expert :)

Just Docker
-----------

To build a Docker container, place your `monitor.ini` and `monitors.ini` files in the top level of the repo (i.e. not in the `docker` directory) and build a container:

```bash
docker build -f docker/monitor.Dockerfile .
```

You should now be able to run this container. Note that if you update your configuration, you will need to rebuild the container.

You should be able to use Alerters OK from this set up, but using loggers may require some work (to get the file(s) out of the container); something like a volume mount I expect. (See note at top of file.)

docker-compose
--------------

The docker-compose stack runs a SimpleMonitor container and a webserver container, so you can use the HTML Logger. It also pre-configures a `_monitor-export` directory between the container and the host you can use to share files.

To use it, place your configuration files in the top level of the repo and build the containers:

```bash
docker-compose build
```

and then you can run it all:

```bash
docker-compose run
```

You can access the webserver on `localhost:8000`. If you update your configuration you will need to rebuild the monitor container: `docker-compose build monitor`.
