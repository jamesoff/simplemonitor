#!/usr/bin/env python3
"""
Configuration Watcher for SimpleMonitor
Monitors configuration files for changes and reloads SimpleMonitor when needed
"""

import os
import time
import hashlib
import requests
import subprocess
import signal
import sys
from pathlib import Path

class ConfigWatcher:
    def __init__(self, config_files=['monitor.ini', 'monitors.ini'], check_interval=30):
        self.config_files = config_files
        self.check_interval = check_interval
        self.last_hashes = {}
        self.webapp_url = os.environ.get('WEBAPP_URL', 'http://webapp:5000')
        self.running = True
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Initialize hashes
        self.update_hashes()
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"Received signal {signum}, shutting down...")
        self.running = False
        sys.exit(0)
    
    def get_file_hash(self, filepath):
        """Get MD5 hash of a file"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except FileNotFoundError:
            return None
    
    def update_hashes(self):
        """Update stored hashes for all config files"""
        for filepath in self.config_files:
            self.last_hashes[filepath] = self.get_file_hash(filepath)
    
    def check_webapp_config(self):
        """Check if webapp has updated configuration"""
        try:
            response = requests.get(f"{self.webapp_url}/api/config-hash", timeout=5)
            if response.status_code == 200:
                data = response.json()
                webapp_hash = data.get('hash', '')
                
                # Compare with local hash
                local_hash = ':'.join([
                    self.last_hashes.get('monitor.ini', ''),
                    self.last_hashes.get('monitors.ini', '')
                ])
                
                if webapp_hash != local_hash and webapp_hash != 'no-config':
                    print(f"Configuration change detected: {webapp_hash} != {local_hash}")
                    return True
        except Exception as e:
            print(f"Error checking webapp config: {e}")
        
        return False
    
    def reload_simplemonitor(self):
        """Reload SimpleMonitor configuration"""
        try:
            print("Reloading SimpleMonitor configuration...")
            
            # Method 1: Try to send SIGHUP to SimpleMonitor process
            result = subprocess.run(['pkill', '-HUP', 'simplemonitor'], 
                                 capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("SimpleMonitor configuration reloaded via SIGHUP")
                return True
            else:
                # Method 2: Try to restart via webapp API
                try:
                    response = requests.post(f"{self.webapp_url}/api/reload-config", 
                                           timeout=10)
                    if response.status_code == 200:
                        print("SimpleMonitor configuration reloaded via API")
                        return True
                except Exception as e:
                    print(f"API reload failed: {e}")
                
                print("Failed to reload SimpleMonitor configuration")
                return False
                
        except Exception as e:
            print(f"Error reloading SimpleMonitor: {e}")
            return False
    
    def check_local_changes(self):
        """Check for local file changes"""
        changes_detected = False
        
        for filepath in self.config_files:
            current_hash = self.get_file_hash(filepath)
            last_hash = self.last_hashes.get(filepath)
            
            if current_hash != last_hash and current_hash is not None:
                print(f"Local change detected in {filepath}")
                changes_detected = True
                self.last_hashes[filepath] = current_hash
        
        return changes_detected
    
    def run(self):
        """Main monitoring loop"""
        print("Configuration watcher started...")
        print(f"Monitoring files: {self.config_files}")
        print(f"Check interval: {self.check_interval} seconds")
        print(f"Webapp URL: {self.webapp_url}")
        
        while self.running:
            try:
                # Check for local file changes
                if self.check_local_changes():
                    if self.reload_simplemonitor():
                        print("Configuration reloaded successfully")
                    else:
                        print("Failed to reload configuration")
                
                # Check for webapp changes
                if self.check_webapp_config():
                    if self.reload_simplemonitor():
                        print("Configuration reloaded from webapp changes")
                        # Update local hashes to match webapp
                        self.update_hashes()
                    else:
                        print("Failed to reload configuration from webapp")
                
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                print("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval)
        
        print("Configuration watcher stopped")

if __name__ == '__main__':
    watcher = ConfigWatcher()
    watcher.run()
