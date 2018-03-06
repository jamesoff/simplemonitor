FROM python:2.7-alpine

WORKDIR /usr/src/app
ENV HTTP_PORT 8012
ENV SRC /usr/src/app/simplemonitor

EXPOSE ${HTTP_PORT}

# Add packages
RUN apk add --update \
    bind-tools \
  && rm -rf /var/cache/apk/*

# Download and install Simplemonitor
ADD https://github.com/jamesoff/simplemonitor/tarball/master /tmp
RUN mkdir -p ${SRC} && \
    tar -xzf /tmp/master -C /tmp/ && \
    mv /tmp/jamesoff-simplemonitor-*/* ${SRC} && \
    rm -fr /tmp/

# Setup Python Environment
RUN pip install --no-cache-dir -r ${SRC}/requirements.txt
RUN python -V

# Copy configuration files 
COPY monitor.ini /config/
COPY monitors.ini /config/

# Move HTML content to config folder
RUN mv ${SRC}/html /config/

# Start the monitor
COPY start.py ${SRC}
RUN chmod u+x ${SRC}/start.py
CMD ["python", "/usr/src/app/simplemonitor/start.py"]
