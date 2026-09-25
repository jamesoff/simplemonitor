Web Interface
=============

SimpleMonitor includes a comprehensive web interface built with Flask and Bootstrap for easy management and monitoring.

Overview
--------

The web interface provides a modern, responsive interface for managing SimpleMonitor configurations and viewing real-time monitoring data. It includes user authentication, monitor management, and real-time dashboard capabilities.

Features
--------

User Authentication
~~~~~~~~~~~~~~~~~~~

- **Admin Account Creation**: Secure setup process for initial admin account
- **Session Management**: Persistent login sessions
- **Role-based Access**: Admin privileges for configuration management
- **Secure Authentication**: Password hashing and session security

Dashboard
~~~~~~~~~

The main dashboard provides:

- **Overview Statistics**: Total monitors, active monitors, SMS alerts, HTTP checks
- **Recent Monitors**: Quick view of recently added monitors
- **Status Summary**: Visual indicators for monitor health
- **Quick Actions**: Direct links to add monitors and view real-time status

Real-time Dashboard
~~~~~~~~~~~~~~~~~~~

The real-time dashboard replicates the original SimpleMonitor status page with enhanced features:

- **Live Updates**: Auto-refresh capabilities with configurable intervals
- **Status Indicators**: Visual status badges for each monitor
- **Summary Bar**: Real-time summary of monitor status
- **Detailed Information**: Complete monitor details including uptime, failures, and age
- **Auto-refresh Controls**: Start/stop auto-refresh with configurable intervals

Monitor Management
~~~~~~~~~~~~~~~~~~

Complete monitor lifecycle management:

- **Add Monitors**: Dynamic form for adding different monitor types
- **Edit Monitors**: Modify existing monitor configurations
- **Delete Monitors**: Remove monitors with confirmation
- **Toggle Status**: Enable/disable monitors without deletion
- **View Details**: Detailed view of monitor configuration and status

Monitor Types Supported
~~~~~~~~~~~~~~~~~~~~~~~

The web interface supports all SimpleMonitor monitor types:

- **HTTP**: URL monitoring with content validation
- **Ping**: Host connectivity testing
- **TCP**: Port availability checking
- **DNS**: DNS record validation
- **Disk Space**: Storage monitoring
- **Memory**: System memory monitoring
- **Process**: Process existence checking
- **Command**: Custom command execution
- **Service**: System service monitoring

Settings Management
~~~~~~~~~~~~~~~~~~~

Centralized configuration management:

- **Twilio Integration**: SMS alerting configuration
- **API Keys**: Secure storage of external service credentials
- **System Settings**: Global configuration options
- **Alert Configuration**: SMS phone numbers and alert preferences

API Endpoints
-------------

The web interface provides RESTful API endpoints:

Status API
~~~~~~~~~~

.. code-block:: http

   GET /api/status

Returns real-time monitoring status including:
- Summary statistics (OK/failed counts)
- Monitor details
- Last update timestamp
- Refresh status

Configuration API
~~~~~~~~~~~~~~~~~

.. code-block:: http

   GET /api/config-hash
   POST /api/reload-config

Configuration management endpoints:
- Get configuration hash for change detection
- Trigger configuration reload

User Interface
--------------

Navigation
~~~~~~~~~~

The interface includes a responsive navigation bar with:

- **Dashboard**: Main overview page
- **Monitors**: Monitor management interface
- **Real-time**: Live monitoring dashboard
- **Add Monitor**: Quick access to add new monitors (admin only)
- **Settings**: Configuration management (admin only)
- **User Menu**: Account management and logout

Responsive Design
~~~~~~~~~~~~~~~~~

The interface is built with Bootstrap for responsive design:

- **Mobile Friendly**: Optimized for mobile devices
- **Tablet Support**: Responsive layout for tablets
- **Desktop Optimized**: Full-featured desktop interface
- **Cross-browser**: Compatible with modern browsers

Status Indicators
~~~~~~~~~~~~~~~~~

Visual status indicators throughout the interface:

- **Success**: Green badges and icons for healthy monitors
- **Warning**: Yellow indicators for disabled or warning states
- **Error**: Red indicators for failed monitors
- **Info**: Blue indicators for informational content

Getting Started
---------------

Initial Setup
~~~~~~~~~~~~~

1. **Access Setup Page**:
   - Navigate to http://localhost:5001/setup
   - Create your admin account
   - Complete the setup process

2. **Login**:
   - Use your admin credentials to log in
   - Access the main dashboard

3. **Add Monitors**:
   - Click "Add Monitor" in the navigation
   - Select monitor type
   - Configure monitor settings
   - Save and activate

Adding Monitors
~~~~~~~~~~~~~~~

1. **Select Monitor Type**:
   - Choose from available monitor types
   - Each type has specific configuration options

2. **Configure Settings**:
   - Fill in required fields (marked with *)
   - Set optional parameters
   - Configure alerting options

3. **SMS Alerts** (Optional):
   - Enable SMS alerts
   - Enter phone number
   - Configure Twilio settings in Settings page

4. **Save and Activate**:
   - Save the monitor configuration
   - Monitor will be automatically added to SimpleMonitor
   - Configuration will be reloaded automatically

Managing Monitors
~~~~~~~~~~~~~~~~~

**View Monitors**:
- Access the Monitors page
- View all configured monitors
- See real-time status

**Edit Monitors**:
- Click the edit button for any monitor
- Modify configuration
- Save changes

**Toggle Status**:
- Enable/disable monitors without deletion
- Use the toggle button in the actions column

**Delete Monitors**:
- Click the delete button
- Confirm deletion
- Monitor will be removed from configuration

Real-time Monitoring
~~~~~~~~~~~~~~~~~~~~

**Access Real-time Dashboard**:
- Click "Real-time" in navigation
- View live monitoring data
- See status updates in real-time

**Configure Auto-refresh**:
- Use the refresh interval dropdown
- Start/stop auto-refresh
- Monitor refresh status

**View Details**:
- Click on monitor names for detailed view
- See complete configuration
- View historical information

Settings Configuration
~~~~~~~~~~~~~~~~~~~~~~

**Twilio SMS Setup**:
1. Navigate to Settings page
2. Enter Twilio Account SID
3. Enter Twilio Auth Token
4. Save settings

**SMS Alert Configuration**:
1. When adding/editing monitors
2. Enable SMS alerts checkbox
3. Enter phone number
4. Save monitor configuration

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Login Issues**:
- Verify admin account exists
- Check password is correct
- Clear browser cache and cookies

**Monitor Not Updating**:
- Check monitor configuration
- Verify SimpleMonitor service is running
- Check container logs

**SMS Not Working**:
- Verify Twilio credentials
- Check phone number format
- Ensure Twilio account has credits

**Real-time Dashboard Not Loading**:
- Check webapp container status
- Verify API endpoints are accessible
- Check browser console for errors

Browser Compatibility
~~~~~~~~~~~~~~~~~~~~~

Supported browsers:
- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

Required features:
- JavaScript enabled
- Local storage support
- Fetch API support

Security Considerations
-----------------------

Authentication
~~~~~~~~~~~~~~

- **Password Hashing**: Passwords are hashed using Werkzeug
- **Session Security**: Secure session management
- **CSRF Protection**: Built-in CSRF protection
- **Input Validation**: All inputs are validated and sanitized

Data Protection
~~~~~~~~~~~~~~~

- **Database Security**: SQLite database with proper permissions
- **Configuration Files**: Secure file permissions
- **API Security**: Protected API endpoints
- **HTTPS**: Use HTTPS in production

Best Practices
~~~~~~~~~~~~~~

- **Regular Backups**: Backup database and configuration files
- **Strong Passwords**: Use strong, unique passwords
- **Regular Updates**: Keep containers updated
- **Monitor Access**: Limit access to management interface
- **Log Monitoring**: Monitor application logs

Advanced Usage
--------------

Custom Monitor Types
~~~~~~~~~~~~~~~~~~~~

To add custom monitor types:

1. **Create Monitor Class**:
   - Extend base monitor class
   - Implement required methods
   - Add to simplemonitor/Monitors/

2. **Update Web Interface**:
   - Add monitor type to webapp.py
   - Create form template
   - Add validation logic

3. **Deploy Changes**:
   - Rebuild containers
   - Test new monitor type

API Integration
~~~~~~~~~~~~~~~

The web interface provides APIs for integration:

- **Status Data**: Real-time monitoring data
- **Configuration Management**: Add/remove monitors
- **Alert Management**: Configure alerting

Example API usage:

.. code-block:: python

   import requests
   
   # Get status
   response = requests.get('http://localhost:5001/api/status')
   status = response.json()
   
   # Get configuration hash
   response = requests.get('http://localhost:5001/api/config-hash')
   config_hash = response.json()['hash']

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

- **Database Indexing**: Optimize database queries
- **Caching**: Implement caching for frequently accessed data
- **Load Balancing**: Use multiple webapp instances
- **CDN**: Use CDN for static assets

Monitoring and Alerting
~~~~~~~~~~~~~~~~~~~~~~~

- **Health Checks**: Monitor web interface health
- **Error Tracking**: Track and alert on errors
- **Performance Monitoring**: Monitor response times
- **Uptime Monitoring**: Monitor service availability

Support and Resources
---------------------

Documentation
~~~~~~~~~~~~~

- **API Documentation**: Available in web interface
- **Configuration Guide**: See configuration.rst
- **Docker Deployment**: See docker-deployment.rst

Community
~~~~~~~~~

- **GitHub Issues**: Report bugs and request features
- **GitHub Discussions**: Ask questions and share ideas
- **Contributing**: See CONTRIBUTING.md

Professional Support
~~~~~~~~~~~~~~~~~~~~

For enterprise support and custom development:
- Contact: james at jamesoff dot net
- GitHub: https://github.com/jamesoff/simplemonitor
