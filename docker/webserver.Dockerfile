# -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# >> nginx @ alpine
# -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
FROM nginx:1.15.1-alpine

# >> meta :: labels
LABEL   version_dockerfile="10-07-2018:prod" \
        version_image="nginx:1.15.1-alpine"

# >> package :: install
RUN     apk --no-cache add --update \
            # __ install :: basics
            build-base \
            openssl \
            # __ install :: tools
            bash
