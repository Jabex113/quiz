def handler(request, context):
    """
    Simplified handler that doesn't depend on the main app.py
    This can be used to test if basic serverless functionality is working.
    """
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': '{"status":"ok","message":"Simple API is working","service":"Campus Quiz"}'
    } 