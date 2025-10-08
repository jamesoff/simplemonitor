#!/usr/bin/env python3
"""
SimpleMonitor Web Interface
A Flask-based web interface for managing SimpleMonitor configurations
"""

import os
import json
import configparser
import subprocess
import signal
import time
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import requests
from twilio.rest import Client
from bs4 import BeautifulSoup

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////code/webapp/simplemonitor.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Monitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    monitor_type = db.Column(db.String(50), nullable=False)
    config = db.Column(db.Text, nullable=False)  # JSON config
    enabled = db.Column(db.Boolean, default=True)
    sms_enabled = db.Column(db.Boolean, default=False)
    sms_phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Real-time status fields (not stored in DB, populated at runtime)
    status = None
    host = None
    detail = None
    uptime = None
    failures = None
    last_failure = None
    age = None

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def sync_monitors_from_service():
    """Sync monitors from SimpleMonitor service to database"""
    try:
        # Get monitors from SimpleMonitor status page
        response = requests.get('http://webserver:80', timeout=5)
        if response.status_code == 200:
            # Parse HTML to extract monitor data
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', class_='table')
            
            if table:
                # Get existing monitors from database
                existing_monitors = {m.name: m for m in Monitor.query.all()}
                
                # Extract monitor data from table
                rows = table.find_all('tr')[1:]  # Skip header row
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 10:  # Ensure we have enough columns
                        monitor_name = cells[0].get_text(strip=True)
                        status = cells[1].get_text(strip=True)
                        host = cells[2].get_text(strip=True)
                        failed_at = cells[3].get_text(strip=True)
                        vfc = cells[4].get_text(strip=True)
                        uptime = cells[5].get_text(strip=True)
                        detail = cells[6].get_text(strip=True)
                        failures = cells[7].get_text(strip=True)
                        last_failure = cells[8].get_text(strip=True)
                        age = cells[9].get_text(strip=True)
                        
                        # Check if monitor already exists in database
                        if monitor_name not in existing_monitors:
                            # Create new monitor in database
                            new_monitor = Monitor(
                                name=monitor_name,
                                monitor_type='unknown',  # We don't have this info from HTML
                                enabled=True,
                                config=json.dumps({
                                    'host': host,
                                    'detail': detail,
                                    'uptime': uptime,
                                    'failures': failures,
                                    'last_failure': last_failure,
                                    'age': age,
                                    'status': status,
                                    'failed_at': failed_at,
                                    'vfc': vfc
                                }),
                                sms_enabled=False,
                                sms_phone='',
                                created_at=datetime.utcnow(),
                                updated_at=datetime.utcnow()
                            )
                            db.session.add(new_monitor)
                            print(f"Added monitor '{monitor_name}' to database")
                        else:
                            # Update existing monitor with latest status
                            existing_monitor = existing_monitors[monitor_name]
                            existing_monitor.config = json.dumps({
                                'host': host,
                                'detail': detail,
                                'uptime': uptime,
                                'failures': failures,
                                'last_failure': last_failure,
                                'age': age,
                                'status': status,
                                'failed_at': failed_at,
                                'vfc': vfc
                            })
                            existing_monitor.updated_at = datetime.utcnow()
                            print(f"Updated monitor '{monitor_name}' in database")
                
                # Commit changes
                db.session.commit()
                print("Monitor sync completed successfully")
                return True
    except Exception as e:
        print(f"Error syncing monitors: {e}")
        db.session.rollback()
        return False

# Monitor type definitions
MONITOR_TYPES = {
    'host': {
        'name': 'Host Ping',
        'description': 'Check if a host is pingable',
        'fields': [
            {'name': 'host', 'type': 'text', 'label': 'Host/IP', 'required': True, 'placeholder': '8.8.8.8'},
            {'name': 'tolerance', 'type': 'number', 'label': 'Tolerance', 'required': False, 'default': '2'},
        ]
    },
    'http': {
        'name': 'HTTP Check',
        'description': 'Check if a URL returns HTTP 200',
        'fields': [
            {'name': 'url', 'type': 'url', 'label': 'URL', 'required': True, 'placeholder': 'https://example.com'},
            {'name': 'tolerance', 'type': 'number', 'label': 'Tolerance', 'required': False, 'default': '1'},
            {'name': 'timeout', 'type': 'number', 'label': 'Timeout (seconds)', 'required': False, 'default': '5'},
        ]
    },
    'dns': {
        'name': 'DNS Check',
        'description': 'Check if a DNS record is resolvable',
        'fields': [
            {'name': 'record', 'type': 'text', 'label': 'DNS Record', 'required': True, 'placeholder': 'google.com'},
            {'name': 'record_type', 'type': 'select', 'label': 'Record Type', 'required': False, 'options': ['A', 'AAAA', 'MX', 'CNAME'], 'default': 'A'},
            {'name': 'tolerance', 'type': 'number', 'label': 'Tolerance', 'required': False, 'default': '1'},
        ]
    },
    'diskspace': {
        'name': 'Disk Space',
        'description': 'Check available disk space',
        'fields': [
            {'name': 'partition', 'type': 'text', 'label': 'Partition', 'required': True, 'placeholder': '/'},
            {'name': 'limit', 'type': 'text', 'label': 'Minimum Free Space', 'required': True, 'placeholder': '1G'},
            {'name': 'tolerance', 'type': 'number', 'label': 'Tolerance', 'required': False, 'default': '1'},
        ]
    },
    'memory': {
        'name': 'Memory Check',
        'description': 'Check available memory',
        'fields': [
            {'name': 'percent_free', 'type': 'number', 'label': 'Minimum Free %', 'required': True, 'placeholder': '10'},
            {'name': 'tolerance', 'type': 'number', 'label': 'Tolerance', 'required': False, 'default': '1'},
        ]
    },
    'process': {
        'name': 'Process Check',
        'description': 'Check if a process is running',
        'fields': [
            {'name': 'process_name', 'type': 'text', 'label': 'Process Name', 'required': True, 'placeholder': 'python3'},
            {'name': 'min_count', 'type': 'number', 'label': 'Minimum Count', 'required': False, 'default': '1'},
            {'name': 'max_count', 'type': 'number', 'label': 'Maximum Count', 'required': False},
            {'name': 'tolerance', 'type': 'number', 'label': 'Tolerance', 'required': False, 'default': '1'},
        ]
    },
    'command': {
        'name': 'Command Check',
        'description': 'Execute a command and check its output',
        'fields': [
            {'name': 'command', 'type': 'text', 'label': 'Command', 'required': True, 'placeholder': 'uptime'},
            {'name': 'result_regexp', 'type': 'text', 'label': 'Expected Regex', 'required': False},
            {'name': 'result_max', 'type': 'number', 'label': 'Max Result Value', 'required': False},
            {'name': 'tolerance', 'type': 'number', 'label': 'Tolerance', 'required': False, 'default': '1'},
        ]
    }
}

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user:
            flash('User not found', 'error')
            session.clear()
            return redirect(url_for('login'))
        if not user.is_admin:
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """Setup admin account"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('setup.html')
        
        # Check if admin already exists
        if User.query.filter_by(is_admin=True).first():
            flash('Admin account already exists', 'error')
            return redirect(url_for('login'))
        
        # Create admin user
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            is_admin=True
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Admin account created successfully', 'success')
        return redirect(url_for('login'))
    
    # Check if admin already exists
    if User.query.filter_by(is_admin=True).first():
        flash('Admin account already exists', 'error')
        return redirect(url_for('login'))
    
    return render_template('setup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash('Logged in successfully', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    monitors = Monitor.query.all()
    return render_template('dashboard.html', monitors=monitors)

@app.route('/realtime')
@login_required
def realtime_dashboard():
    """Real-time dashboard page"""
    # Sync monitors from service first
    sync_monitors_from_service()
    return render_template('realtime_dashboard.html')

@app.route('/monitors')
@login_required
def monitors():
    """Monitor management page"""
    # Sync monitors from service first
    sync_monitors_from_service()
    
    # Get monitors from database (now synced)
    db_monitors = Monitor.query.all()
    
    # Get monitors from SimpleMonitor status for real-time data
    try:
        response = requests.get('http://localhost:5001/api/status', timeout=5)
        if response.status_code == 200:
            status_data = response.json()
            if status_data['status'] == 'success':
                # Create a mapping of monitor names to their real-time status
                status_map = {m['name']: m for m in status_data['monitors']}
                
                # Update database monitors with real-time status
                for monitor in db_monitors:
                    if monitor.name in status_map:
                        status_data = status_map[monitor.name]
                        monitor.status = status_data['status']
                        monitor.host = status_data.get('host', '')
                        monitor.detail = status_data.get('detail', '')
                        monitor.uptime = status_data.get('uptime', '')
                        monitor.failures = status_data.get('failures', '')
                        monitor.last_failure = status_data.get('last_failure', '')
                        monitor.age = status_data.get('age', '')
                
                all_monitors = db_monitors
            else:
                all_monitors = db_monitors
        else:
            all_monitors = db_monitors
    except:
        all_monitors = db_monitors
    
    return render_template('monitors.html', monitors=all_monitors, monitor_types=MONITOR_TYPES)

@app.route('/monitors/add', methods=['GET', 'POST'])
@admin_required
def add_monitor():
    """Add new monitor"""
    if request.method == 'POST':
        name = request.form['name']
        monitor_type = request.form['monitor_type']
        sms_enabled = 'sms_enabled' in request.form
        sms_phone = request.form.get('sms_phone', '')
        
        # Build config from form data
        config = {}
        for key, value in request.form.items():
            if key.startswith('config_') and value:
                config[key[7:]] = value  # Remove 'config_' prefix
        
        # Validate required fields
        required_fields = MONITOR_TYPES[monitor_type]['fields']
        for field in required_fields:
            if field['required'] and field['name'] not in config:
                flash(f"Field '{field['label']}' is required", 'error')
                return render_template('add_monitor.html', monitor_types=MONITOR_TYPES, selected_type=monitor_type)
        
        # Create monitor
        monitor = Monitor(
            name=name,
            monitor_type=monitor_type,
            config=json.dumps(config),
            sms_enabled=sms_enabled,
            sms_phone=sms_phone
        )
        
        try:
            db.session.add(monitor)
            db.session.commit()
            flash('Monitor added successfully', 'success')
            
            # Reload SimpleMonitor configuration
            reload_simplemonitor_config()
            
            return redirect(url_for('monitors'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding monitor: {str(e)}', 'error')
    
    return render_template('add_monitor.html', monitor_types=MONITOR_TYPES)

@app.route('/monitors/<int:monitor_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_monitor(monitor_id):
    """Edit monitor"""
    monitor = Monitor.query.get_or_404(monitor_id)
    
    if request.method == 'POST':
        monitor.name = request.form['name']
        monitor.monitor_type = request.form['monitor_type']
        monitor.sms_enabled = 'sms_enabled' in request.form
        monitor.sms_phone = request.form.get('sms_phone', '')
        
        # Build config from form data
        config = {}
        for key, value in request.form.items():
            if key.startswith('config_') and value:
                config[key[7:]] = value
        
        monitor.config = json.dumps(config)
        monitor.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            flash('Monitor updated successfully', 'success')
            reload_simplemonitor_config()
            return redirect(url_for('monitors'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating monitor: {str(e)}', 'error')
    
    config = json.loads(monitor.config) if monitor.config else {}
    return render_template('edit_monitor.html', monitor=monitor, monitor_types=MONITOR_TYPES, config=config)

@app.route('/monitors/<int:monitor_id>')
@login_required
def view_monitor(monitor_id):
    """View monitor details"""
    monitor = Monitor.query.get_or_404(monitor_id)
    config = json.loads(monitor.config) if monitor.config else {}
    return render_template('view_monitor.html', monitor=monitor, config=config)

@app.route('/monitors/<int:monitor_id>/toggle', methods=['POST'])
@admin_required
def toggle_monitor(monitor_id):
    """Toggle monitor enabled/disabled status"""
    monitor = Monitor.query.get_or_404(monitor_id)
    
    try:
        monitor.enabled = not monitor.enabled
        monitor.updated_at = datetime.utcnow()
        db.session.commit()
        
        status = "enabled" if monitor.enabled else "disabled"
        flash(f'Monitor {status} successfully', 'success')
        reload_simplemonitor_config()
    except Exception as e:
        db.session.rollback()
        flash(f'Error toggling monitor: {str(e)}', 'error')
    
    return redirect(url_for('monitors'))

@app.route('/monitors/<int:monitor_id>/delete', methods=['POST'])
@admin_required
def delete_monitor(monitor_id):
    """Delete monitor"""
    monitor = Monitor.query.get_or_404(monitor_id)
    
    try:
        db.session.delete(monitor)
        db.session.commit()
        flash('Monitor deleted successfully', 'success')
        reload_simplemonitor_config()
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting monitor: {str(e)}', 'error')
    
    return redirect(url_for('monitors'))

@app.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    """Settings page"""
    if request.method == 'POST':
        # Update settings
        twilio_sid = request.form.get('twilio_sid', '')
        twilio_token = request.form.get('twilio_token', '')
        twilio_from = request.form.get('twilio_from', '')
        
        settings_to_update = {
            'twilio_sid': twilio_sid,
            'twilio_token': twilio_token,
            'twilio_from': twilio_from
        }
        
        for key, value in settings_to_update.items():
            setting = Settings.query.filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                setting = Settings(key=key, value=value)
                db.session.add(setting)
        
        try:
            db.session.commit()
            flash('Settings updated successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating settings: {str(e)}', 'error')
    
    # Get current settings
    settings = {}
    for setting in Settings.query.all():
        settings[setting.key] = setting.value
    
    return render_template('settings.html', settings=settings)

@app.route('/api/config-hash')
def api_config_hash():
    """API endpoint for SimpleMonitor to check configuration changes"""
    return jsonify({'hash': get_config_hash()})

@app.route('/api/reload-config', methods=['POST'])
def api_reload_config():
    """API endpoint to trigger configuration reload"""
    try:
        reload_simplemonitor_config()
        return jsonify({'status': 'success', 'message': 'Configuration reloaded'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/status')
def api_status():
    """API endpoint to get current monitoring status"""
    try:
        # Try to get status from SimpleMonitor status page
        status_url = 'http://webserver:80'
        response = requests.get(status_url, timeout=5)
        
        if response.status_code == 200:
            # Parse the HTML to extract status information
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract summary information
            summary = soup.find('div', {'id': 'summary'})
            updated_info = soup.find('div', {'id': 'updated'})
            refresh_status = soup.find('div', {'id': 'refresh_status'})
            
            # Extract monitor data from table
            monitors_data = []
            table = soup.find('table', class_='table')
            if table:
                rows = table.find_all('tr')[1:]  # Skip header row
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 10:  # Ensure we have enough columns
                        detail_text = cells[6].get_text(strip=True)
                        
                        # Extract response time from detail field
                        response_time = None
                        response_time_ms = None
                        
                        # Look for patterns like "200 in 0.19s", "0.19s", "123ms", etc.
                        import re
                        time_patterns = [
                            r'(\d+(?:\.\d+)?)\s*s(?:econds?)?',  # "0.19s", "1.5s"
                            r'(\d+(?:\.\d+)?)\s*ms',  # "123ms"
                            r'in\s+(\d+(?:\.\d+)?)\s*s',  # "in 0.19s"
                            r'in\s+(\d+(?:\.\d+)?)\s*ms'  # "in 123ms"
                        ]
                        
                        for pattern in time_patterns:
                            match = re.search(pattern, detail_text, re.IGNORECASE)
                            if match:
                                time_value = float(match.group(1))
                                if 'ms' in pattern:
                                    response_time_ms = int(time_value)
                                    response_time = f"{response_time_ms}ms"
                                else:
                                    response_time_ms = int(time_value * 1000)
                                    response_time = f"{response_time_ms}ms"
                                break
                        
                        monitor_data = {
                            'name': cells[0].get_text(strip=True),
                            'status': cells[1].get_text(strip=True),
                            'host': cells[2].get_text(strip=True),
                            'failed_at': cells[3].get_text(strip=True),
                            'vfc': cells[4].get_text(strip=True),
                            'uptime': cells[5].get_text(strip=True),
                            'detail': detail_text,
                            'response_time': response_time or 'N/A',
                            'response_time_ms': response_time_ms,
                            'failures': cells[7].get_text(strip=True),
                            'last_failure': cells[8].get_text(strip=True),
                            'age': cells[9].get_text(strip=True)
                        }
                        monitors_data.append(monitor_data)
            
            # Extract summary stats
            summary_text = summary.get_text() if summary else ""
            ok_count = 0
            fail_count = 0
            
            # Count OK and failed monitors
            for monitor in monitors_data:
                if 'OK' in monitor['status']:
                    ok_count += 1
                else:
                    fail_count += 1
            
            return jsonify({
                'status': 'success',
                'summary': {
                    'ok': ok_count,
                    'failed': fail_count,
                    'total': len(monitors_data)
                },
                'updated': updated_info.get_text(strip=True) if updated_info else 'Unknown',
                'refresh_status': refresh_status.get_text(strip=True) if refresh_status else '',
                'monitors': monitors_data,
                'timestamp': int(time.time())
            })
        else:
            return jsonify({'status': 'error', 'message': 'Failed to fetch status'}), 500
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def get_config_hash():
    """Get hash of current configuration for change detection"""
    try:
        with open('monitor.ini', 'rb') as f:
            monitor_hash = hashlib.md5(f.read()).hexdigest()
        with open('monitors.ini', 'rb') as f:
            monitors_hash = hashlib.md5(f.read()).hexdigest()
        return f"{monitor_hash}:{monitors_hash}"
    except FileNotFoundError:
        return "no-config"

def reload_simplemonitor_config():
    """Reload SimpleMonitor configuration"""
    try:
        # Generate new configuration files
        generate_monitor_ini()
        generate_monitors_ini()
        
        # Update configuration hash
        config_hash = get_config_hash()
        
        # Try to reload SimpleMonitor using Docker API
        try:
            # Method 1: Try to send SIGHUP to the monitor container
            result = subprocess.run([
                'docker', 'exec', 'simplemonitor-monitor-1', 
                'pkill', '-HUP', 'simplemonitor'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                flash('SimpleMonitor configuration reloaded successfully', 'success')
            else:
                # Method 2: Restart the monitor container
                subprocess.run([
                    'docker', 'restart', 'simplemonitor-monitor-1'
                ], check=True, timeout=30)
                flash('SimpleMonitor container restarted with new configuration', 'success')
                
        except subprocess.TimeoutExpired:
            flash('Configuration reload timed out, but files were updated', 'warning')
        except subprocess.CalledProcessError as e:
            flash(f'Error reloading SimpleMonitor: {e}', 'error')
        except FileNotFoundError:
            # Docker not available, just update files
            flash('Configuration files updated (Docker not available for reload)', 'info')
            
    except Exception as e:
        flash(f'Error updating configuration: {str(e)}', 'error')

def generate_monitor_ini():
    """Generate monitor.ini from database"""
    config = configparser.ConfigParser()
    
    # Monitor section
    config['monitor'] = {
        'interval': '60',
        'monitors': 'monitors.ini'
    }
    
    # Reporting section
    config['reporting'] = {
        'loggers': 'html,logfile'
    }
    
    # HTML logger
    config['html'] = {
        'type': 'html',
        'filename': 'index.html',
        'folder': 'html',
        'tz': 'UTC'
    }
    
    # Log file logger
    config['logfile'] = {
        'type': 'logfile',
        'filename': 'monitor.log'
    }
    
    # Add SMS alerter if any monitors have SMS enabled
    sms_monitors = Monitor.query.filter_by(sms_enabled=True).first()
    if sms_monitors:
        twilio_sid = Settings.query.filter_by(key='twilio_sid').first()
        twilio_token = Settings.query.filter_by(key='twilio_token').first()
        twilio_from = Settings.query.filter_by(key='twilio_from').first()
        
        if twilio_sid and twilio_token and twilio_from:
            config['reporting']['alerters'] = 'sms'
            config['sms'] = {
                'type': 'twilio_sms',
                'account_sid': twilio_sid.value,
                'auth_token': twilio_token.value,
                'target': '+1234567890',  # This will be overridden per monitor
                'sender': twilio_from.value
            }
    
    # Write to file
    with open('monitor.ini', 'w') as f:
        config.write(f)

def generate_monitors_ini():
    """Generate monitors.ini from database"""
    config = configparser.ConfigParser()
    
    # Defaults
    config['defaults'] = {
        'tolerance': '2'
    }
    
    # Add monitors from database
    for monitor in Monitor.query.filter_by(enabled=True).all():
        monitor_config = json.loads(monitor.config)
        monitor_config['type'] = monitor.monitor_type
        
        # Add SMS phone if enabled
        if monitor.sms_enabled and monitor.sms_phone:
            monitor_config['sms_phone'] = monitor.sms_phone
        
        config[monitor.name] = monitor_config
    
    # Write to file
    with open('monitors.ini', 'w') as f:
        config.write(f)

def send_sms_alert(phone_number, message):
    """Send SMS alert via Twilio"""
    try:
        twilio_sid = Settings.query.filter_by(key='twilio_sid').first()
        twilio_token = Settings.query.filter_by(key='twilio_token').first()
        twilio_from = Settings.query.filter_by(key='twilio_from').first()
        
        if not all([twilio_sid, twilio_token, twilio_from]):
            return False
        
        client = Client(twilio_sid.value, twilio_token.value)
        message = client.messages.create(
            body=message,
            from_=twilio_from.value,
            to=phone_number
        )
        return True
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")
    app.run(host='0.0.0.0', port=5000, debug=False)
