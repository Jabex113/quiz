from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        "status": "ok",
        "message": "API is working!",
        "app": "Campus Quiz"
    })

def handler(request, context):
    """Simple test handler for Vercel."""
    # Get the path
    path = request.get('path', '/')
    
    # Basic response
    if path == '/':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': '{"status":"ok","message":"Simple test function is working"}'
        }
    
    # Default response
    return {
        'statusCode': 404,
        'headers': {'Content-Type': 'application/json'},
        'body': '{"status":"error","message":"Not found"}'
    } 