from app import app

# This file is used by Vercel to run the Flask app
# The app object is imported from app.py

# Make the app available to Vercel
def handler(request, **kwargs):
    return app(request)

if __name__ == '__main__':
    app.run(debug=True) 