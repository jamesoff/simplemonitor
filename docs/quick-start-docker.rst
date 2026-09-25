Quick Start with Docker
=======================

Get SimpleMonitor running with Docker in just a few minutes.

Prerequisites
-------------

- Docker and Docker Compose installed
- Git (to clone the repository)
- Basic familiarity with command line

Installation
------------

1. **Clone the repository**:

   .. code-block:: bash

      git clone https://github.com/jamesoff/simplemonitor.git
      cd simplemonitor

2. **Start the services**:

   .. code-block:: bash

      docker-compose up -d

3. **Wait for services to start** (about 30-60 seconds):

   .. code-block:: bash

      docker-compose ps

   You should see three services running:
   - simplemonitor-monitor-1
   - simplemonitor-webapp-1  
   - simplemonitor-webserver-1

Access the Interfaces
---------------------

- **Web Management Interface**: http://localhost:5001
- **Status Dashboard**: http://localhost:8000

Initial Setup
-------------

1. **Create Admin Account**:
   - Navigate to http://localhost:5001/setup
   - Enter your admin username and password
   - Click "Create Admin Account"

2. **Login to Web Interface**:
   - Go to http://localhost:5001
   - Use your admin credentials to log in

3. **Add Your First Monitor**:
   - Click "Add Monitor" in the navigation
   - Select "HTTP" monitor type
   - Enter a URL to monitor (e.g., https://google.com)
   - Click "Save Monitor"

4. **View Real-time Status**:
   - Click "Real-time" in the navigation
   - See your monitor status updating in real-time
   - Enable auto-refresh for live updates

Quick Configuration
-------------------

**Basic HTTP Monitor**:
- Monitor Type: HTTP
- Name: My Website
- URL: https://example.com
- Interval: 60 seconds

**Ping Monitor**:
- Monitor Type: Ping
- Name: Router Ping
- Host: 192.168.1.1
- Interval: 30 seconds

**SMS Alerts** (Optional):
1. Go to Settings page
2. Enter Twilio credentials
3. When adding monitors, enable SMS alerts
4. Enter your phone number

Stopping the Services
---------------------

To stop all services:

.. code-block:: bash

   docker-compose down

To stop and remove all data:

.. code-block:: bash

   docker-compose down -v

Troubleshooting
---------------

**Services not starting**:
- Check if ports 5001 and 8000 are available
- Run ``docker-compose logs`` to see error messages

**Web interface not accessible**:
- Wait a few minutes for services to fully start
- Check ``docker-compose logs webapp``

**Monitor not working**:
- Check monitor configuration
- Verify the target is accessible
- Check ``docker-compose logs monitor``

Next Steps
----------

- **Read the full documentation**: See :ref:`Docker Deployment<docker-deployment>`
- **Learn about the web interface**: See :ref:`Web Interface<web-interface>`
- **Configure advanced features**: See :ref:`Configuration<configuration>`
- **Add custom monitors**: See :ref:`Creating Monitors<creating-monitors>`

Need Help?
----------

- **GitHub Issues**: https://github.com/jamesoff/simplemonitor/issues
- **Documentation**: https://simplemonitor.readthedocs.io/
- **Community**: GitHub Discussions
