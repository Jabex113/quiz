import sys
import os
import json
import traceback
from flask import Flask, request

# Add parent directory to path so we can import from app.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create a simple handler first before trying to import the main app
def basic_handler(request, context):
    """Basic handler that returns a simple response."""
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': '<html><body><h1>Basic Handler Working</h1><p>This is the fallback handler</p></body></html>'
    }

try:
    # Import the Flask app from the main app.py file
    from app import app as flask_app
    
    def handler(request, context):
        """Handle requests and route them to the Flask app"""
        try:
            # Debug information
            debug_info = {
                'request_method': request.get('method', 'GET'),
                'request_path': request.get('path', '/'),
                'python_version': sys.version,
                'sys_path': sys.path
            }
            
            # For debugging purposes, for simple paths just return basic info
            if request.get('path', '/') in ['/', '/debug']:
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'status': 'ok', 
                        'message': 'Debug mode active',
                        'debug_info': debug_info
                    })
                }
                
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
            status_code = [200]
            response_headers = [{'Content-Type': 'text/html'}]

            def start_response(status, headers, exc_info=None):
                status_code[0] = int(status.split(' ')[0])
                response_headers[0] = dict(headers)
                return lambda x: response_data.append(x)

            # Get response from Flask app
            try:
                # Call the Flask app with the WSGI environment
                response_iter = flask_app(environ, start_response)
                response_body = b''

                # Collect all response chunks
                for chunk in response_iter:
                    if chunk:  # Skip empty chunks
                        response_body += chunk if isinstance(chunk, bytes) else chunk.encode('utf-8')

                # Close the iterator if it's closeable
                if hasattr(response_iter, 'close'):
                    response_iter.close()

                # Convert bytes to string if needed
                if isinstance(response_body, bytes):
                    try:
                        response_body = response_body.decode('utf-8')
                    except UnicodeDecodeError:
                        # If we can't decode as UTF-8, use base64 encoding
                        response_body = base64.b64encode(response_body).decode('ascii')
                        response_headers[0]['Content-Encoding'] = 'base64'

                return {
                    'statusCode': status_code[0],
                    'headers': response_headers[0],
                    'body': response_body
                }
            except Exception as e:
                error_info = {
                    'error': str(e),
                    'traceback': traceback.format_exc(),
                    'debug_info': debug_info
                }
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps(error_info)
                }
        except Exception as outer_e:
            # If there's an error in the handler itself, return basic error info
            error_info = {
                'error': f'Handler error: {str(outer_e)}',
                'traceback': traceback.format_exc()
            }
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps(error_info)
            }

except Exception as import_error:
    # If there's an error importing the app, use the basic handler instead
    error_info = {
        'error': f'Import error: {str(import_error)}',
        'traceback': traceback.format_exc()
    }
    
    def handler(request, context):
        """Fallback handler when main app import fails"""
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(error_info)
        } 