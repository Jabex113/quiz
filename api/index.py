import sys
import os
from flask import Flask, request

# Add parent directory to path so we can import from app.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app from the main app.py file
from app import app as flask_app

def handler(request, context):
    """Handle requests and route them to the Flask app"""
    # Convert Vercel request format to WSGI format
    method = request.get('method', 'GET')
    path = request.get('path', '/')
    headers = request.get('headers', {})
    body = request.get('body', '')
    
    # Create a mock environment for the Flask app
    environ = {
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
        'QUERY_STRING': request.get('query', ''),
        'SERVER_NAME': 'vercel',
        'SERVER_PORT': '443',
        'HTTP_HOST': headers.get('host', 'localhost'),
        'wsgi.url_scheme': 'https',
        'wsgi.input': body,
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False
    }
    
    # Add HTTP headers
    for key, value in headers.items():
        key = key.upper().replace('-', '_')
        if key not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            key = 'HTTP_' + key
        environ[key] = value
    
    # Handle the request using the Flask app
    response_data = []
    
    def start_response(status, response_headers, exc_info=None):
        status_code = int(status.split(' ')[0])
        headers_dict = dict(response_headers)
        return lambda x: response_data.append(x)
    
    # Get response from Flask app
    try:
        response_body = b''.join(flask_app(environ, start_response))
        if isinstance(response_body, bytes):
            response_body = response_body.decode('utf-8')
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/html'},
            'body': response_body
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': f'{{"error": "Server error: {str(e)}"}}'
        } 