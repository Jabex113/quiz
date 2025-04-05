import sys
import os

# Add parent directory to path so we can import from app.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def handler(request, context):
    """Basic handler that returns a simple HTML response."""
    # Return a basic HTML page to show that the function is working
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Campus Quiz</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    display: flex; 
                    flex-direction: column; 
                    align-items: center; 
                    justify-content: center; 
                    height: 100vh; 
                    margin: 0;
                    background-color: #f5f5f5;
                }
                .container {
                    text-align: center;
                    padding: 30px;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                    max-width: 600px;
                }
                h1 { color: #4f46e5; }
                p { margin: 20px 0; }
                .btn {
                    display: inline-block;
                    background: #4f46e5;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 5px;
                    text-decoration: none;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Campus Quiz</h1>
                <p>We are currently deploying the full application. Thank you for your patience!</p>
                <p>Basic functionality is now working on Vercel.</p>
                <a href="/test" class="btn">Check Test API</a>
            </div>
        </body>
        </html>
        """
    } 