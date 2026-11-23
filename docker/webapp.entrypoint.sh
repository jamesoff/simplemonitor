#!/bin/bash

# ENVs
# == == == == == == == == == == == == == == ==
# >> env :: web/docker paths
# ENV     DOCKER_ROOT=/code \
#         DOCKER_WEBAPP_ROOT=/code/webapp \
#         DOCKER_ENTRYPOINT_BINARY=/bin/webapp.entrypoint.sh \
#         DOCKER_ENTRYPOINT_ORIGIN=/code/docker/webapp.entrypoint.sh

# >> env :: source/host paths
# ENV     SOURCE_ROOT=./

# >> env :: user/groups
# ENV     MAIN_USER=simplemonitor \
#         MAIN_USER_ID=1500 \
#         MAIN_GROUP=simplemonitor \
#         MAIN_GROUP_ID=1500

echo "environment vars  == == == == == == == == =="
echo "== == == == == == == == == == == == == == =="
echo "DOCKER_ROOT               "$DOCKER_ROOT
echo "DOCKER_WEBAPP_ROOT        "$DOCKER_WEBAPP_ROOT
echo "SOURCE_ROOT               "$SOURCE_ROOT
echo "DOCKER_ENTRYPOINT_BINARY  "$DOCKER_ENTRYPOINT_BINARY
echo "DOCKER_ENTRYPOINT_ORIGIN  "$DOCKER_ENTRYPOINT_ORIGIN
echo "MAIN_USER                 "$MAIN_USER
echo "MAIN_USER_ID              "$MAIN_USER_ID
echo "MAIN_GROUP                "$MAIN_GROUP
echo "MAIN_GROUP_ID             "$MAIN_GROUP_ID

# exec webapp
# == == == == == == == == == == == == == == ==
cd /code
python start_services.py

# exec some other commands
# == == == == == == == == == == == == == == ==
exec "$@"
