from app import app, handler

# This file is used by Vercel to serve the application
# The 'app' object is the WSGI application
# The 'handler' function is for serverless function invocation

def vercel_handler(request, *args, **kwargs):
    """Wrapper function to handle Vercel serverless requests."""
    return handler(request) 