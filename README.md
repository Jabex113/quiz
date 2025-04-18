# Enhanced Quiz Platform

A powerful assessment builder for teachers with comprehensive features for creating and administering quizzes and exams.

## Features

### Assessment Builder
- Create assessments with title/objective and description
- Author attribution with first name and last name (e.g., Henri Leon)
- Grade level selection (Grades 11-12)
- Organize by category/strand

### Question Types
1. **Multiple Choice**
   - Create questions with 4 options
   - Mark correct answer

2. **True or False**
   - Simple true/false questions

3. **Short Answer**
   - Define expected answers

4. **Fill in the Blank**
   - Create questions with blank spaces
   - Define correct answers for each blank

5. **Matching**
   - Create matching items for left and right columns
   - Define correct matches

### Time Management
- Set time limits for each question
- Automatic progression when time expires
- Total quiz time limit with countdown
- Visual progress bar for time remaining

### Academic Integrity
- Webcam monitoring during exams
- Detailed reporting of potential issues

### Results and Analysis
- Immediate scoring and feedback
- Detailed question-by-question review
- Visual score representation
- Pass/fail determination

## Getting Started

### Installation
1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   ```
   cp .env.example .env
   ```
   Edit `.env` with your email and API settings

### Running the Application
```
python app.py
```

### Admin Access
1. Navigate to `/nimda/login`
2. Login with admin credentials
3. Create quizzes and questions

## Technical Details

### Technologies Used
- Flask (Python web framework)
- JavaScript for interactive features
- HTML/CSS for frontend
- AI integration for content detection

### Files and Structure
- `app.py`: Main application logic
- `templates/`: HTML templates
- `static/`: CSS, JS, and assets
- `quizzes.txt`: Quiz storage
- `users.txt`: User accounts

## License
This project is licensed under the MIT License

## Deployment Instructions



1. Clone the repository
2. Create a `.env` file based on `.env.example`
3. Install dependencies: `pip install -r requirements.txt`
4. Run the application: `python app.py`

## Troubleshooting

If you encounter a "Serverless Function has crashed" error:

1. Check your environment variables in Vercel
2. Visit the `/simple` endpoint to test the simplified handler
3. Check the Vercel logs for detailed error information