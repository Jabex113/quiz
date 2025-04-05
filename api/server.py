from flask import Flask
import sys
import os

# Add parent directory to path so we can import from app.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the actual Flask app 
from app import app as flask_app

# Verify that flask_app routes have been imported correctly
print(f"Flask app imported with {len(flask_app.url_map._rules)} routes")

# This handler is called by Vercel
def handler(request, context):
    """Handler for Vercel serverless function - returns the main Flask application."""
    return flask_app 