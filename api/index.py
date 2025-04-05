def handler(request, context):
    """Minimal handler to avoid any potential issues"""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html"},
        "body": "<html><body><h1>Hello from Campus Quiz!</h1><p>Basic API is working</p></body></html>"
    } 