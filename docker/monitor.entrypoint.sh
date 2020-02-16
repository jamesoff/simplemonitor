#!/bin/bash

# ENVs
# == == == == == == == == == == == == == == ==
# >> env :: web/docker paths
# ENV     DOCKER_ROOT=/code \
#         DOCKER_HTML_BACKUP=/code/html-backup \
#         DOCKER_ENTRYPOINT_BINARY=/bin/docker.entrypoint.sh \
#         DOCKER_ENTRYPOINT_ORIGIN=/code/docker/docker.entrypoint.sh

# >> env :: source/host paths
# ENV     SOURCE_ROOT=./ \
#         SOURCE_HTML_ROOT=./html/

# >> env :: user/groups
# ENV     MAIN_USER=simplemonitor \
#         MAIN_USER_ID=1500 \
#         MAIN_GROUP=simplemonitor \
#         MAIN_GROUP_ID=1500

# >> env :: volumes
# ENV     VOLUME_UNIVERSAL_HTML=/code/html

if [ ! -f /code/init.flag ]; then
    # copy :: html (workaround for docker-volumes)
    # == == == == == == == == == == == == == == ==
    cp -r "$DOCKER_HTML_BACKUP"/* $DOCKER_HTML_ROOT

    # fix docker issue with right-levels on volumes
    # == == == == == == == == == == == == == == ==
    chown -R $MAIN_USER:$MAIN_GROUP $VOLUME_UNIVERSAL_HTML
    chmod -R 777 $VOLUME_UNIVERSAL_HTML

    chown -R $MAIN_USER:$MAIN_GROUP $VOLUME_MONITOR_EXPORT
    chmod -R 777 $VOLUME_MONITOR_EXPORT

    # set file-flag
    # == == == == == == == == == == == == == == ==
    su-exec $DOCKER_USER:$DOCKER_GROUP touch /code/init.flag
fi

echo "environment vars  == == == == == == == == =="
echo "== == == == == == == == == == == == == == =="
echo "DOCKER_ROOT               "$DOCKER_ROOT
echo "DOCKER_HTML_ROOT          "$DOCKER_HTML_ROOT
echo "DOCKER_HTML_BACKUP        "$DOCKER_HTML_BACKUP
echo "SOURCE_ROOT               "$SOURCE_ROOT
echo "SOURCE_HTML_ROOT          "$SOURCE_HTML_ROOT
echo "DOCKER_ENTRYPOINT_BINARY  "$DOCKER_ENTRYPOINT_BINARY
echo "DOCKER_ENTRYPOINT_ORIGIN  "$DOCKER_ENTRYPOINT_ORIGIN
echo "MAIN_USER                 "$MAIN_USER
echo "MAIN_USER_ID              "$MAIN_USER_ID
echo "MAIN_GROUP                "$MAIN_GROUP
echo "MAIN_GROUP_ID             "$MAIN_GROUP_ID
echo "VOLUME_UNIVERSAL_HTML     "$VOLUME_UNIVERSAL_HTML
echo "VOLUME_MONITOR_EXPORT     "$VOLUME_MONITOR_EXPORT

# exec entrypoint.py
# == == == == == == == == == == == == == == ==
python /code/monitor.py

# exec some other commands
# == == == == == == == == == == == == == == ==
exec "$@"
