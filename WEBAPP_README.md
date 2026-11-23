# SimpleMonitor Web Interface

A Flask-based web interface for managing SimpleMonitor configurations with authentication, monitor management, and SMS alerting.

## Features

- **Authentication System**: Secure login with admin account setup
- **Monitor Management**: Add, edit, and delete monitors through a web UI
- **Dynamic Forms**: Automatically generated forms for different monitor types
- **SMS Alerts**: Configure Twilio SMS alerts for monitor failures
- **Real-time Status**: View monitor status and configuration
- **Settings Management**: Configure API keys and system settings

## Monitor Types Supported

- **Host Ping**: Check if a host is pingable
- **HTTP Check**: Verify web services are responding
- **DNS Check**: Test DNS resolution
- **Disk Space**: Monitor available disk space
- **Memory Check**: Monitor system memory usage
- **Process Check**: Verify processes are running
- **Command Check**: Execute custom commands

## Quick Start

1. **Start the services**:
   ```bash
   docker-compose up --build -d
   ```

2. **Access the web interface**:
   - Web Interface: http://localhost:5001
   - Status Page: http://localhost:8000

3. **Setup admin account**:
   - Go to http://localhost:5001/setup
   - Create your admin account

4. **Configure Twilio (optional)**:
   - Go to Settings page
   - Enter your Twilio credentials
   - Enable SMS alerts for monitors

## URLs

- `/` - Landing page (shows SimpleMonitor status)
- `/setup` - Setup admin account (first time only)
- `/login` - Login page
- `/dashboard` - Main dashboard
- `/monitors` - Monitor management
- `/monitors/add` - Add new monitor
- `/settings` - System settings

## Configuration

The web interface automatically generates SimpleMonitor configuration files:
- `monitor.ini` - Main configuration
- `monitors.ini` - Monitor definitions

Configuration is automatically reloaded when changes are made through the web interface.

## SMS Alerts

To enable SMS alerts:

1. Sign up for a Twilio account
2. Get your Account SID and Auth Token
3. Purchase a phone number for sending SMS
4. Configure these in the Settings page
5. Enable SMS alerts when adding/editing monitors

## Development

The web interface is built with:
- Flask (Python web framework)
- Bootstrap 5 (UI framework)
- SQLite (database)
- Twilio (SMS service)

## Security Notes

- Change the SECRET_KEY in docker-compose.yml for production
- Use strong passwords for admin accounts
- Consider using HTTPS in production
- Regularly update dependencies
