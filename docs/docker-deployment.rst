Docker Deployment
=================

SimpleMonitor now includes a comprehensive Docker-based deployment strategy with a web interface for easy management and monitoring.

Overview
--------

The Docker deployment consists of three main components:

1. **SimpleMonitor Service** - The core monitoring engine
2. **Web Interface** - Flask-based web application for management
3. **Web Server** - Nginx server for serving status pages

Architecture
------------

.. image:: docker-architecture.png
   :alt: Docker Architecture Diagram
   :align: center

The deployment uses Docker Compose to orchestrate multiple containers:

- **monitor**: Runs the SimpleMonitor service with configuration watching
- **webapp**: Flask web application for management interface
- **webserver**: Nginx server for serving status pages

Quick Start
-----------

1. **Clone the repository**:

   .. code-block:: bash

      git clone https://github.com/jamesoff/simplemonitor.git
      cd simplemonitor

2. **Start the services**:

   .. code-block:: bash

      docker-compose up -d

3. **Access the interfaces**:

   - Web Management Interface: http://localhost:5001
   - Status Dashboard: http://localhost:8000

4. **Set up admin account**:

   - Navigate to http://localhost:5001/setup
   - Create your admin account
   - Start adding monitors through the web interface

Features
--------

Web Management Interface
~~~~~~~~~~~~~~~~~~~~~~~~

The web interface provides:

- **Dashboard**: Overview of all monitors with real-time status
- **Real-time Dashboard**: Live monitoring with auto-refresh capabilities
- **Monitor Management**: Add, edit, delete, and toggle monitors
- **Settings**: Configure Twilio SMS alerts and other settings
- **User Management**: Admin account creation and management

Real-time Monitoring
~~~~~~~~~~~~~~~~~~~~

The real-time dashboard replicates the original SimpleMonitor status page with:

- Auto-refresh capabilities (10s, 30s, 1min, 5min intervals)
- Live status updates
- Summary statistics
- Detailed monitor information
- Visual status indicators

Configuration Management
~~~~~~~~~~~~~~~~~~~~~~~~

- **Dynamic Configuration**: Monitors added through the web interface are automatically added to SimpleMonitor
- **Configuration Watching**: The monitor service watches for configuration changes and reloads automatically
- **Persistent Storage**: All configurations are stored in SQLite database and configuration files

Docker Services
---------------

Monitor Service
~~~~~~~~~~~~~~~

The monitor service runs SimpleMonitor with enhanced features:

- **Configuration Watcher**: Automatically detects configuration changes
- **Auto-reload**: Reloads SimpleMonitor when configurations change
- **Optimized Build**: Layered Docker build for efficient caching

Web Application
~~~~~~~~~~~~~~~

The Flask web application provides:

- **RESTful API**: For real-time status data
- **Database Management**: SQLite database for storing monitor configurations
- **Authentication**: Secure login system with admin privileges
- **Twilio Integration**: SMS alerting capabilities

Web Server
~~~~~~~~~~

The Nginx web server:

- **Status Pages**: Serves the SimpleMonitor status page
- **Static Files**: Serves static assets for the web interface
- **Load Balancing**: Can be configured for high availability

Configuration Files
-------------------

The deployment uses several configuration files:

- **docker-compose.yml**: Main orchestration file
- **monitor.ini**: SimpleMonitor main configuration
- **monitors.ini**: Monitor definitions
- **requirements-webapp.txt**: Python dependencies for web app

Environment Variables
---------------------

The following environment variables can be configured:

- **SECRET_KEY**: Flask secret key for sessions (required)
- **WEBAPP_URL**: URL for webapp service (for monitor communication)

Docker Compose Configuration
----------------------------

The docker-compose.yml file defines three services:

.. code-block:: yaml

   version: '2'
   
   services:
     monitor:
       build:
         context: ./
         dockerfile: ./docker/monitor.Dockerfile
       volumes:
         - http-content:/code/html
         - ./_monitor-export:/code/monitor-export
       environment:
         - WEBAPP_URL=http://webapp:5000
       restart: always
       depends_on:
         - webserver
   
     webserver:
       build:
         context: ./
         dockerfile: ./docker/webserver.Dockerfile
       ports:
         - "8000:80"
       volumes:
         - http-content:/usr/share/nginx/html
       restart: always
   
     webapp:
       build:
         context: ./
         dockerfile: ./docker/webapp.Dockerfile
       ports:
         - "5001:5000"
       volumes:
         - ./simplemonitor.db:/code/simplemonitor.db
         - ./monitor.ini:/code/monitor.ini
         - ./monitors.ini:/code/monitors.ini
         - /var/run/docker.sock:/var/run/docker.sock
       environment:
         - SECRET_KEY=your-secret-key-change-in-production
       restart: always
       depends_on:
         - monitor

Production Deployment
---------------------

For production deployment, consider the following:

1. **Change Default Secrets**:
   - Update SECRET_KEY in docker-compose.yml
   - Use strong, unique passwords

2. **SSL/TLS Configuration**:
   - Configure reverse proxy with SSL certificates
   - Update port mappings as needed

3. **Database Backup**:
   - Regular backups of simplemonitor.db
   - Backup configuration files

4. **Monitoring**:
   - Monitor container health
   - Set up log aggregation
   - Configure alerting for container failures

5. **Security**:
   - Restrict Docker socket access
   - Use secrets management
   - Regular security updates

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Containers not starting**:
   - Check Docker and Docker Compose versions
   - Verify port availability
   - Check logs: ``docker-compose logs``

**Web interface not accessible**:
   - Verify port 5001 is available
   - Check webapp container logs
   - Ensure database is initialized

**Monitor service not updating**:
   - Check configuration file permissions
   - Verify volume mounts
   - Check monitor container logs

**Status page not updating**:
   - Verify webserver container is running
   - Check volume mounts for html content
   - Ensure monitor service is generating status page

Logs and Debugging
~~~~~~~~~~~~~~~~~~

View logs for specific services:

.. code-block:: bash

   # All services
   docker-compose logs
   
   # Specific service
   docker-compose logs webapp
   docker-compose logs monitor
   docker-compose logs webserver
   
   # Follow logs
   docker-compose logs -f webapp

Advanced Configuration
----------------------

Custom Monitor Types
~~~~~~~~~~~~~~~~~~~~

To add custom monitor types:

1. Create monitor class in simplemonitor/Monitors/
2. Update webapp.py to include new monitor type
3. Add UI components in templates/
4. Rebuild containers

Custom Alerters
~~~~~~~~~~~~~~~

To add custom alerters:

1. Create alerter class in simplemonitor/Alerters/
2. Update webapp.py to include new alerter
3. Add configuration options in settings
4. Rebuild containers

Scaling
-------

The deployment can be scaled for high availability:

- **Multiple Monitor Instances**: Run multiple monitor containers
- **Load Balancing**: Use external load balancer
- **Database Clustering**: Use external database
- **Container Orchestration**: Deploy on Kubernetes

Migration from Standalone
-------------------------

To migrate from standalone SimpleMonitor:

1. **Backup Configuration**:
   - Copy monitor.ini and monitors.ini
   - Export any custom monitors/alerters

2. **Deploy Docker Version**:
   - Follow quick start instructions
   - Copy configuration files to project root

3. **Import Configuration**:
   - Use web interface to add monitors
   - Configure alerters through settings

4. **Verify Setup**:
   - Check all monitors are working
   - Test alerting functionality
   - Verify status page updates

Support
-------

For issues and questions:

- **GitHub Issues**: https://github.com/jamesoff/simplemonitor/issues
- **Documentation**: https://simplemonitor.readthedocs.io/
- **Community**: GitHub Discussions
