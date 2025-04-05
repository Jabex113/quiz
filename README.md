# Campus Quiz

A Flask-based quiz application for students.

## Deployment Instructions

### Vercel Deployment

1. Fork this repository to your GitHub account
2. Sign up for a Vercel account and connect it to your GitHub account
3. Create a new project in Vercel and select the forked repository
4. Set up the following environment variables in Vercel:
   - `EMAIL_ADDRESS`: Your email address for OTP functionality
   - `EMAIL_PASSWORD`: Your email app password 
   - `FLASK_SECRET_KEY`: A random string for session security
   - `VERCEL`: Set to "true"
   - `DEEPSEEK_API_KEY`: API key for DeepSeek AI functionality

5. Deploy the project

### Local Development

1. Clone the repository
2. Create a `.env` file based on `.env.example`
3. Install dependencies: `pip install -r requirements.txt`
4. Run the application: `python app.py`

## Troubleshooting

If you encounter a "Serverless Function has crashed" error:

1. Check your environment variables in Vercel
2. Visit the `/simple` endpoint to test the simplified handler
3. Check the Vercel logs for detailed error information