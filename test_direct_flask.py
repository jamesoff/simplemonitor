#!/usr/bin/env python3
import requests
import json

# Create a session to maintain cookies
session = requests.Session()

# Test login
login_data = {
    'username': 'admin',
    'password': 'admin123'
}

print("=== Testing Login ===")
try:
    login_response = session.post('http://localhost:5001/login', data=login_data)
    print(f"Login Status Code: {login_response.status_code}")
    
    if login_response.status_code == 302:
        print("✅ Login successful! Redirected to dashboard.")
    elif login_response.status_code == 200:
        print("❌ Login failed - returned login page")
    else:
        print(f"Unexpected login response: {login_response.status_code}")
        
except Exception as e:
    print(f"Error during login: {e}")

print("\n=== Testing Add Monitor ===")
# Test data for adding a monitor
monitor_data = {
    'name': 'Direct Flask Test Monitor',
    'monitor_type': 'host',
    'config_host': '8.8.8.8',
    'config_tolerance': '2'
}

try:
    add_response = session.post('http://localhost:5001/monitors/add', data=monitor_data)
    print(f"Add Monitor Status Code: {add_response.status_code}")
    
    if add_response.status_code == 302:
        print("✅ Monitor added successfully! Redirected to monitors page.")
    elif add_response.status_code == 200:
        print("❌ Form validation error - returned add monitor page")
        # Check if there are any error messages in the response
        if 'error' in add_response.text.lower() or 'invalid' in add_response.text.lower():
            print("Response contains error messages")
    else:
        print(f"Unexpected status: {add_response.status_code}")
        
except Exception as e:
    print(f"Error: {e}")

# Check if monitor was added
print("\n=== Checking Monitors ===")
try:
    monitors_response = session.get('http://localhost:5001/monitors')
    if 'Direct Flask Test Monitor' in monitors_response.text:
        print("✅ Test monitor found in monitors page")
    else:
        print("❌ No test monitor found")
        
except Exception as e:
    print(f"Error checking monitors: {e}")
