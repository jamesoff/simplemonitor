# -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# >> python @ alpine
# -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
FROM python:3.12-alpine

# >> meta :: labels
LABEL   version_dockerfile="21-01-2024:prod" \
        version_image="python:3.12-alpine"

# >> package :: install (Layer 1: System packages - rarely change)
RUN     apk --no-cache add --update \
            # __ install :: basics
            build-base \
            openssl \
            # __ install :: tools
            bash \
            sudo \
            openrc \
            su-exec \
            bind-tools \
            openssl-dev \
            libffi-dev \
            rust \
            cargo

# >> env :: web/docker paths (Layer 2: Environment variables)
ENV     DOCKER_ROOT=/code \
        DOCKER_HTML_ROOT=/code/html \
        DOCKER_HTML_BACKUP=/code/html-backup \
        DOCKER_ENTRYPOINT_BINARY=/bin/monitor.entrypoint.sh \
        DOCKER_ENTRYPOINT_ORIGIN=/code/docker/monitor.entrypoint.sh

# >> env :: source/host paths
ENV     SOURCE_ROOT=./

# >> env :: volumes
ENV     VOLUME_UNIVERSAL_HTML=$DOCKER_HTML_ROOT \
        VOLUME_MONITOR_EXPORT=/code/monitor-export

# >> env :: user/groups
ENV     MAIN_USER=simplemonitor \
        MAIN_USER_ID=1500 \
        MAIN_GROUP=simplemonitor \
        MAIN_GROUP_ID=1500

# >> setup :: root-directory (Layer 3: Directory structure)
RUN     mkdir -p $DOCKER_ROOT
WORKDIR $DOCKER_ROOT

# >> upgrade pip (Layer 4: Python package manager)
RUN     pip install --upgrade pip

# >> copy requirements first for better caching (Layer 5: Dependencies)
COPY    pyproject.toml poetry.lock README.md ./

# >> copy source code (Layer 6: Application code - changes frequently)
COPY    . .

# >> install package (Layer 7: Install SimpleMonitor)
RUN     pip install --no-cache-dir .

# >> install config watcher dependencies (Layer 8: Additional Python packages)
RUN     pip install --no-cache-dir requests

# >> prepare :: volumes
RUN     mkdir -p $VOLUME_MONITOR_EXPORT $DOCKER_HTML_ROOT

# >> setup :: volumes
VOLUME  $VOLUME_UNIVERSAL_HTML \
        $VOLUME_MONITOR_EXPORT

# >> add :: user, group, project-directory-rights
RUN     addgroup -g $MAIN_GROUP_ID $MAIN_GROUP \
        && adduser -D -G $MAIN_GROUP -u $MAIN_USER_ID $MAIN_USER \
        && chown -R $MAIN_USER:$MAIN_GROUP $DOCKER_ROOT

# >> entrypoint :: prepare
RUN     cp $DOCKER_ENTRYPOINT_ORIGIN $DOCKER_ENTRYPOINT_BINARY \
        && chmod +x $DOCKER_ENTRYPOINT_BINARY

# Start the monitor
CMD     ["/bin/monitor.entrypoint.sh"]
