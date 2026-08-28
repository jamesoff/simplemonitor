# -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# >> python @ alpine
# -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
FROM python:3.12-alpine

# >> meta :: labels
LABEL   version_dockerfile="21-01-2024:webapp" \
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
            cargo \
            # __ install :: docker
            docker-cli

# >> env :: web/docker paths (Layer 2: Environment variables)
ENV     DOCKER_ROOT=/code \
        DOCKER_WEBAPP_ROOT=/code/webapp \
        DOCKER_ENTRYPOINT_BINARY=/bin/webapp.entrypoint.sh \
        DOCKER_ENTRYPOINT_ORIGIN=/code/docker/webapp.entrypoint.sh

# >> env :: source/host paths
ENV     SOURCE_ROOT=./

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
COPY    requirements-webapp.txt ./
RUN     pip install --no-cache-dir -r requirements-webapp.txt

# >> copy source code (Layer 6: Application code - changes frequently)
COPY    . .

# >> prepare :: webapp directory
RUN     mkdir -p $DOCKER_WEBAPP_ROOT

# >> add :: user, group, project-directory-rights
RUN     addgroup -g $MAIN_GROUP_ID $MAIN_GROUP \
        && adduser -D -G $MAIN_GROUP -u $MAIN_USER_ID $MAIN_USER \
        && chown -R $MAIN_USER:$MAIN_GROUP $DOCKER_ROOT

# >> entrypoint :: prepare
RUN     cp $DOCKER_ENTRYPOINT_ORIGIN $DOCKER_ENTRYPOINT_BINARY \
        && chmod +x $DOCKER_ENTRYPOINT_BINARY

# >> expose :: port
EXPOSE  5000

# Start the webapp
CMD     ["/bin/webapp.entrypoint.sh"]
