from flask import Flask, jsonify, redirect, send_from_directory, Response
import os

app = Flask(__name__)

@app.route("/", defaults={"path": ""})
def index(path):
    # Try to serve the index.html file from the root directory
    try:
        return send_from_directory('../', 'index.html')
    except:
        return "Campus Quiz is online! This is a temporary placeholder while the full app is being deployed."

@app.route("/<path:path>")
def catch_all(path):
    # Serve static files if the path starts with static/
    if path.startswith('static/'):
        file_path = path[7:]  # Remove 'static/' from the path
        return send_from_directory('../static', file_path)
    return f"Path: {path} - This is a temporary placeholder while the full app is being deployed."

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "message": "Campus Quiz server is running on Vercel"
    })

# This handler is called by Vercel
def handler(request, context):
    """Handle a request to the Flask application in Vercel's serverless environment."""
    return app 