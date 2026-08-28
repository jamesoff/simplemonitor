#!/usr/bin/env python3
"""
Startup script for Flask web interface
"""

import os
import sys
import time
import signal

def run_webapp():
    """Run Flask webapp"""
    try:
        # Import and run the Flask app
        from webapp import app, db
        print("Initializing database...")
        
        # Ensure we're in the right directory
        import os
        os.chdir('/code')
        
        with app.app_context():
            db.create_all()
            print("Database tables created successfully")
            
            # Sync monitors from service
            from webapp import sync_monitors_from_service
            print("Syncing monitors from service...")
            sync_monitors_from_service()
        print("Starting Flask webapp on port 5000...")
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Error starting Flask app: {e}")
        import traceback
        traceback.print_exc()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\nShutting down webapp...")
    sys.exit(0)

def main():
    """Main startup function"""
    print("Starting SimpleMonitor Flask web interface...")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start Flask app (this will block)
        run_webapp()
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == '__main__':
    main()
