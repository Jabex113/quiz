from flask import Flask, request, render_template, session, redirect, url_for, flash, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
import json
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

USERS_FILE = 'users.txt'
STORIES_FILE = 'database.txt'
QUIZZES_FILE = 'quizzes.txt' 

def init_files():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)
    if not os.path.exists(STORIES_FILE):
        with open(STORIES_FILE, 'w') as f:
            json.dump([], f)
    if not os.path.exists(QUIZZES_FILE):
        with open(QUIZZES_FILE, 'w') as f:
            json.dump([], f)

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def load_stories():
    try:
        with open(STORIES_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_stories(stories):
    with open(STORIES_FILE, 'w') as f:
        json.dump(stories, f, indent=2)

def load_quizzes():
    try:
        with open(QUIZZES_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_quizzes(quizzes):
    with open(QUIZZES_FILE, 'w') as f:
        json.dump(quizzes, f, indent=2)

def get_icons_by_category():
    return {
        'Math': 'fa-square-root-alt',
        'Physics': 'fa-atom',
        'Chemistry': 'fa-flask',
        'Biology': 'fa-dna',
        'Engineering': 'fa-cogs',
        'Programming': 'fa-code',
        'Web Development': 'fa-globe',
        'Database': 'fa-database',
        'Computer Systems': 'fa-desktop',
        'Networking': 'fa-network-wired',
        'Literature': 'fa-book',
        'History': 'fa-landmark',
        'Philosophy': 'fa-brain',
        'Economics': 'fa-chart-line',
        'Political Science': 'fa-balance-scale',
        'Cookery': 'fa-utensils',
        'Beauty Care': 'fa-spa',
        'Computer Hardware': 'fa-desktop',
        'Electronics': 'fa-microchip',
        'Automotive': 'fa-car'
    }

def get_strand_categories(strand):
    categories = {
        'STEM': ['Math', 'Physics', 'Chemistry', 'Biology', 'Engineering'],
        'ICT': ['Programming', 'Networking', 'Web Development', 'Database', 'Computer Systems'],
        'HUMSS': ['Literature', 'History', 'Philosophy', 'Political Science', 'Economics'],
        'TVL': ['Cookery', 'Computer Hardware', 'Beauty Care', 'Automotive', 'Electronics']
    }
    return categories.get(strand, [])

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp):
    try:
        message = MIMEMultipart()
        message['From'] = EMAIL_ADDRESS
        message['To'] = email
        message['Subject'] = 'Verify Your Campus Account'

        html_content = render_template('email/otp.html', otp=otp)
        message.attach(MIMEText(html_content, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(message)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@app.route('/')
def index():
    if 'user_email' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    strand = request.form.get('strand')
    
    if not all([username, email, password, strand]):
        flash('Please fill in all fields', 'error')
        return redirect(url_for('index'))

    users = load_users()
    if email in users:
        flash('Email already registered', 'error')
        return redirect(url_for('index'))

    otp = generate_otp()
    session['signup_data'] = {
        'username': username,
        'email': email,
        'password': password,
        'strand': strand,
        'otp': otp,
        'timestamp': datetime.now().isoformat()
    }

    if not send_otp_email(email, otp):
        flash('Failed to send verification email', 'error')
        return redirect(url_for('index'))

    return render_template('verify_otp.html', email=email)

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    if 'signup_data' not in session:
        flash('Please sign up first', 'error')
        return redirect(url_for('index'))

    signup_data = session['signup_data']
    submitted_otp = ''.join([request.form.get(f'otp{i}', '') for i in range(1, 7)])
    timestamp = datetime.fromisoformat(signup_data['timestamp'])

    if datetime.now() - timestamp > timedelta(minutes=10):
        session.pop('signup_data', None)
        flash('OTP expired. Please try again', 'error')
        return redirect(url_for('index'))

    if submitted_otp != signup_data['otp']:
        flash('Invalid OTP. Please try again', 'error')
        return render_template('verify_otp.html', email=signup_data['email'])

    users = load_users()
    users[signup_data['email']] = {
        'username': signup_data['username'],
        'password': generate_password_hash(signup_data['password'], method='pbkdf2:sha256'),
        'strand': signup_data['strand'],
        'created_at': datetime.now().isoformat(),
        'quiz_history': []  # Initialize quiz history
    }
    save_users(users)

    session.pop('signup_data', None)
    session['user_email'] = signup_data['email']
    session['username'] = signup_data['username']
    session['strand'] = signup_data['strand']

    return redirect(url_for('dashboard'))

@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    if 'signup_data' not in session:
        flash('Please sign up first', 'error')
        return redirect(url_for('index'))

    signup_data = session['signup_data']
    new_otp = generate_otp()
    
    signup_data.update({
        'otp': new_otp,
        'timestamp': datetime.now().isoformat()
    })
    session['signup_data'] = signup_data

    if not send_otp_email(signup_data['email'], new_otp):
        flash('Failed to send verification email', 'error')
        return redirect(url_for('index'))

    return render_template('verify_otp.html', email=signup_data['email'])

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    if not all([email, password]):
        flash('Please fill in all fields', 'error')
        return redirect(url_for('index'))

    users = load_users()
    if email not in users:
        flash('Invalid email or password', 'error')
        return redirect(url_for('index'))

    user = users[email]
    if not check_password_hash(user['password'], password):
        flash('Invalid email or password', 'error')
        return redirect(url_for('index'))

    session['user_email'] = email
    session['username'] = user['username']
    session['strand'] = user['strand']
    
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session:
        return redirect(url_for('index'))

    strand = session['strand']
    quizzes = load_quizzes()
    users = load_users()
    
    # Filter quizzes based on strand and category
    strand_quizzes = [quiz for quiz in quizzes if quiz['strand'] == strand and 'questions' in quiz]
    
    # Add icons based on category
    icons = get_icons_by_category()
    for quiz in strand_quizzes:
        quiz['icon'] = icons.get(quiz['category'], 'fa-question-circle')

    # Calculate user's quiz statistics
    user_quiz_history = users[session['user_email']].get('quiz_history', [])
    total_quizzes = len(user_quiz_history)
    average_score = sum(quiz['score'] for quiz in user_quiz_history) / total_quizzes if total_quizzes > 0 else 0
    perfect_scores = sum(1 for quiz in user_quiz_history if quiz['score'] == 100)

    return render_template('dashboard.html',
                       username=session['username'],
                       strand=session['strand'],
                       quizzes=strand_quizzes,
                       total_quizzes=total_quizzes,
                       average_score=average_score,
                       perfect_scores=perfect_scores)

@app.route('/start_quiz/<quiz_id>')
def start_quiz(quiz_id):
    if 'user_email' not in session:
        return redirect(url_for('index'))

    quizzes = load_quizzes()
    quiz = next((q for q in quizzes if q['id'] == quiz_id), None)
    
    if not quiz or 'questions' not in quiz:
        flash('Quiz not available yet', 'error')
        return redirect(url_for('dashboard'))

    return render_template('quiz.html', quiz=quiz)

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    if 'user_email' not in session:
        return redirect(url_for('index'))

    quiz_id = request.form.get('quiz_id')
    user_answers = request.form.to_dict()

    # Remove non-answer keys
    user_answers.pop('quiz_id', None)

    quizzes = load_quizzes()
    quiz = next((q for q in quizzes if q['id'] == quiz_id), None)
    
    if not quiz or 'questions' not in quiz:
        flash('Invalid quiz', 'error')
        return redirect(url_for('dashboard'))

    # Calculate score
    total_questions = len(quiz['questions'])
    
    # Track correct questions for more detailed review
    correct_questions = []
    incorrect_questions = []

    for i, question in enumerate(quiz['questions']):
        user_answer = user_answers.get(f'question_{i}')
        if user_answer is not None and int(user_answer) == question['correct_answer']:
            correct_questions.append(i)
        else:
            incorrect_questions.append(i)

    correct_answers = len(correct_questions)
    score_percentage = (correct_answers / total_questions) * 100

    # Record user's quiz result
    users = load_users()
    user_email = session['user_email']
    if user_email in users:
        if 'quiz_history' not in users[user_email]:
            users[user_email]['quiz_history'] = []
        
        users[user_email]['quiz_history'].append({
            'quiz_id': quiz_id,
            'quiz_title': quiz['title'],
            'score': score_percentage,
            'date': datetime.now().isoformat()
        })
        save_users(users)

    # Render results page
    return render_template('quiz_results.html', 
                           quiz=quiz, 
                           score=correct_answers, 
                           total=total_questions, 
                           score_percentage=score_percentage,
                           correct_questions=correct_questions)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/nimda/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == 'admin' and password == 'lol':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials', 'error')

    return render_template('nimda/admin_login.html')

@app.route('/nimda/dashboard')
def admin_dashboard():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    quizzes = load_quizzes()
    return render_template('nimda/admin_dashboard.html', quizzes=quizzes)

@app.route('/nimda/post_quiz', methods=['POST'])
def admin_post_quiz():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    strand = request.form.get('strand')
    category = request.form.get('quiz_category')
    title = request.form.get('quiz_title')
    description = request.form.get('quiz_description')
    topics = request.form.get('quiz_topics')

    if not all([strand, category, title, description, topics]):
        flash('All fields are required', 'error')
        return redirect(url_for('admin_dashboard'))

    # Verify category belongs to strand
    strand_categories = get_strand_categories(strand)
    if category not in strand_categories:
        flash('Invalid category for selected strand', 'error')
        return redirect(url_for('admin_dashboard'))

    quizzes = load_quizzes()
    quizzes.append({
        'id': str(random.randint(1000, 9999)),
        'title': title,
        'description': description,
        'topics': topics,
        'category': category,
        'strand': strand,
        'timestamp': datetime.now().isoformat()
    })
    save_quizzes(quizzes)

    flash('Quiz posted successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/nimda/get_quiz_questions/<quiz_id>')
def get_quiz_questions(quiz_id):
    """
    Retrieve questions for a specific quiz
    """
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    quizzes = load_quizzes()
    quiz = next((q for q in quizzes if q['id'] == quiz_id), None)
    
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404

    # If questions don't exist, return empty list
    return jsonify({
        'questions': quiz.get('questions', [])
    })

@app.route('/nimda/save_quiz_questions', methods=['POST'])
def save_quiz_questions():
    """
    Save or update quiz questions
    """
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # Get quiz ID from form
    quiz_id = request.form.get('quiz_id')
    
    # Collect questions data
    questions = []
    index = 0
    
    # Collect questions dynamically
    while f'questions[{index}]' in request.form or (index == 0 and 'questions[]' in request.form):
        # Determine the key for the current question
        question_key = 'questions[]' if index == 0 else f'questions[{index}]'
        
        # Get question text
        question_text = request.form.getlist(question_key)[0]
        
        # Collect options for this question
        options_key = f'options_{index+1}[]'
        options = request.form.getlist(options_key)
        
        # Get correct answer
        correct_key = f'correct_{index+1}'
        correct_answer = int(request.form.get(correct_key, 0))
        
        # Create question object
        question = {
            'question': question_text,
            'options': options,
            'correct_answer': correct_answer
        }
        
        questions.append(question)
        index += 1

    # Load existing quizzes
    quizzes = load_quizzes()
    
    # Find and update the specific quiz
    for quiz in quizzes:
        if quiz['id'] == quiz_id:
            quiz['questions'] = questions
            break
    
    # Save updated quizzes
    save_quizzes(quizzes)
    
    return jsonify({'success': True}), 200

@app.route('/nimda/delete_quiz/<quiz_id>', methods=['POST'])
def admin_delete_quiz(quiz_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    quizzes = load_quizzes()
    quizzes = [quiz for quiz in quizzes if quiz['id'] != quiz_id]
    save_quizzes(quizzes)

    return '', 204

@app.route('/get_categories/<strand>')
def get_categories(strand):
    categories = get_strand_categories(strand)
    return {'categories': categories}

init_files()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)