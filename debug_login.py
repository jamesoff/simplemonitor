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
    # First, get the login page to see if there are any issues
    login_page_response = session.get('http://localhost:5001/login')
    print(f"Login page status: {login_page_response.status_code}")
    
    # Now try to login
    login_response = session.post('http://localhost:5001/login', data=login_data)
    print(f"Login POST status: {login_response.status_code}")
    print(f"Response headers: {dict(login_response.headers)}")
    
    # Check if we got redirected
    if login_response.status_code == 302:
        print("✅ Login successful! Got redirect.")
        print(f"Redirect location: {login_response.headers.get('Location', 'None')}")
    elif login_response.status_code == 200:
        print("❌ Login failed - returned login page")
        # Check if there are any error messages
        if 'Invalid username or password' in login_response.text:
            print("Error: Invalid username or password")
        elif 'Logged in successfully' in login_response.text:
            print("Success message found but no redirect")
        else:
            print("No clear error or success message")
    else:
        print(f"Unexpected status: {login_response.status_code}")
        
    # Try to access a protected page
    print("\n=== Testing Protected Page Access ===")
    dashboard_response = session.get('http://localhost:5001/dashboard')
    print(f"Dashboard status: {dashboard_response.status_code}")
    
    if dashboard_response.status_code == 200:
        print("✅ Successfully accessed dashboard")
    elif dashboard_response.status_code == 302:
        print("❌ Redirected to login (session not maintained)")
        print(f"Redirect location: {dashboard_response.headers.get('Location', 'None')}")
    else:
        print(f"Unexpected dashboard status: {dashboard_response.status_code}")
        
except Exception as e:
    print(f"Error: {e}")
