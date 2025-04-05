from flask import Flask
import sys, os, json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Flask app from app.py
from app import app

def handler(request, context):
    """Handle requests to the Flask application in Vercel serverless environment."""
    try:
        # Get path and method from request
        path = request.get('path', '/')
        method = request.get('method', 'GET')
        
        # Create WSGI environ
        environ = {
            'wsgi.input': None,
            'wsgi.errors': sys.stderr,
            'wsgi.version': (1, 0),
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
            'wsgi.url_scheme': 'https',
            'PATH_INFO': path,
            'QUERY_STRING': '',
            'REQUEST_METHOD': method,
            'SERVER_NAME': 'vercel-serverless',
            'SERVER_PORT': '443',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'CONTENT_LENGTH': '',
            'CONTENT_TYPE': '',
            # Add common headers
            'HTTP_HOST': request.get('headers', {}).get('host', 'vercel-serverless'),
            'HTTP_USER_AGENT': request.get('headers', {}).get('user-agent', ''),
            'HTTP_ACCEPT': request.get('headers', {}).get('accept', '*/*'),
        }
        
        # Add query parameters
        if 'query' in request and request['query']:
            environ['QUERY_STRING'] = '&'.join(f"{k}={v}" for k, v in request['query'].items())
        
        # Handle body for POST/PUT requests
        if method in ['POST', 'PUT'] and 'body' in request and request['body']:
            body_data = request['body']
            environ['wsgi.input'] = body_data
            environ['CONTENT_LENGTH'] = str(len(body_data))
            environ['CONTENT_TYPE'] = request.get('headers', {}).get('content-type', 'application/json')
        
        # Store headers for response
        headers = []
        
        # Prepare response handler
        def start_response(status, response_headers, exc_info=None):
            status_code = int(status.split()[0])
            headers.extend(response_headers)
            return lambda x: None  # Dummy write function
        
        # Call Flask app
        response_body = b''
        for data in app(environ, start_response):
            if data:
                response_body += data if isinstance(data, bytes) else data.encode('utf-8')
        
        # Convert headers to dict format for Vercel
        headers_dict = {}
        for k, v in headers:
            headers_dict[k] = v
        
        # Return formatted response
        return {
            'statusCode': int(headers[0][1].split()[0]) if headers and len(headers[0]) > 1 else 200,
            'headers': headers_dict,
            'body': response_body.decode('utf-8')
        }
    
    except Exception as e:
        # Return error response
        error_message = f"Error processing request: {str(e)}"
        print(error_message, file=sys.stderr)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/plain'},
            'body': error_message
        } 