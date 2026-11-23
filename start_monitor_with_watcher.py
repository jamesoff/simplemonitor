#!/usr/bin/env python3
"""
Start SimpleMonitor with configuration watcher
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

def run_simplemonitor():
    """Run SimpleMonitor in the background"""
    try:
        print("Starting SimpleMonitor...")
        process = subprocess.Popen(['simplemonitor'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        print(f"SimpleMonitor started with PID: {process.pid}")
        return process
    except Exception as e:
        print(f"Error starting SimpleMonitor: {e}")
        return None

def run_config_watcher():
    """Run configuration watcher"""
    try:
        print("Starting configuration watcher...")
        from config_watcher import ConfigWatcher
        watcher = ConfigWatcher()
        watcher.run()
    except Exception as e:
        print(f"Error starting config watcher: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\nReceived signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Main startup function"""
    print("Starting SimpleMonitor with configuration watcher...")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start SimpleMonitor
    monitor_process = run_simplemonitor()
    if not monitor_process:
        print("Failed to start SimpleMonitor")
        sys.exit(1)
    
    # Wait a moment for SimpleMonitor to start
    time.sleep(2)
    
    try:
        # Start config watcher in a separate thread
        watcher_thread = threading.Thread(target=run_config_watcher, daemon=True)
        watcher_thread.start()
        
        # Wait for SimpleMonitor process
        monitor_process.wait()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Clean up SimpleMonitor process
        if monitor_process:
            monitor_process.terminate()
            monitor_process.wait()

if __name__ == '__main__':
    main()
