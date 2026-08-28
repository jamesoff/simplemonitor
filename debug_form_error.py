#!/usr/bin/env python3
import requests
import re
from bs4 import BeautifulSoup

# Create a session to maintain cookies
session = requests.Session()

# Login
login_data = {'username': 'admin', 'password': 'admin123'}
session.post('http://localhost:5001/login', data=login_data)

# Test form submission
monitor_data = {
    'name': 'Debug Monitor',
    'monitor_type': 'host',
    'config_host': '8.8.8.8',
    'config_tolerance': '2'
}

response = session.post('http://localhost:5001/monitors/add', data=monitor_data)
print(f"Status Code: {response.status_code}")

# Parse the HTML to find error messages
soup = BeautifulSoup(response.text, 'html.parser')

# Look for alert messages
alerts = soup.find_all('div', class_='alert')
print(f"\nFound {len(alerts)} alert messages:")
for i, alert in enumerate(alerts, 1):
    print(f"Alert {i}: {alert.get_text(strip=True)}")

# Look for invalid feedback messages
invalid_feedbacks = soup.find_all('div', class_='invalid-feedback')
print(f"\nFound {len(invalid_feedbacks)} invalid feedback messages:")
for i, feedback in enumerate(invalid_feedbacks, 1):
    if feedback.get_text(strip=True):
        print(f"Invalid feedback {i}: {feedback.get_text(strip=True)}")

# Look for any text containing "error" or "required"
error_text = soup.find_all(text=re.compile(r'error|required|invalid', re.I))
print(f"\nFound {len(error_text)} error-related text elements:")
for i, text in enumerate(error_text[:10], 1):  # Limit to first 10
    if text.strip():
        print(f"Error text {i}: {text.strip()}")

# Check if the form has validation classes
form = soup.find('form', id='monitorForm')
if form:
    print(f"\nForm validation classes: {form.get('class', [])}")
    
    # Check input fields for validation classes
    inputs = form.find_all('input')
    for input_field in inputs:
        name = input_field.get('name', 'unnamed')
        classes = input_field.get('class', [])
        if 'is-invalid' in classes or 'is-valid' in classes:
            print(f"Input '{name}' classes: {classes}")
