def handler(request, context):
    """A simple health check endpoint to test Vercel's serverless functions."""
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/plain'},
        'body': 'API is working! Your Flask app should be available at the root URL.'
    } 