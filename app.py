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
import requests
from datetime import datetime, timedelta
import base64
import numpy as np
import cv2
import io

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

# DeepSeek API key - load from environment variable or use default for development
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', "sk-289d0e34995441d9b01e878fbaa61e2b")

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
        'Automotive': 'fa-car',
        'Accounting': 'fa-calculator',
        'Business Management': 'fa-briefcase',
        'Marketing': 'fa-bullhorn',
        'Finance': 'fa-money-bill-wave',
        'Entrepreneurship': 'fa-store'
    }

def get_strand_categories(strand):
    categories = {
        'STEM': ['Math', 'Physics', 'Chemistry', 'Biology', 'Engineering'],
        'ICT': ['Programming', 'Networking', 'Web Development', 'Database', 'Computer Systems'],
        'HUMSS': ['Literature', 'History', 'Philosophy', 'Political Science', 'Economics'],
        'TVL': ['Cookery', 'Computer Hardware', 'Beauty Care', 'Automotive', 'Electronics'],
        'ABM': ['Accounting', 'Business Management', 'Marketing', 'Finance', 'Entrepreneurship']
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

    # Get user data
    user = users[session['user_email']]

    # Get user's quiz history
    user_quiz_history = user.get('quiz_history', [])

    # Get IDs of completed quizzes
    user_completed_quizzes = [attempt['quiz_id'] for attempt in user_quiz_history]

    # Get account creation date
    account_created = user.get('created_at', None)
    if account_created:
        try:
            account_created = datetime.fromisoformat(account_created).strftime('%B %d, %Y')
        except:
            account_created = 'N/A'

    return render_template('dashboard_new.html',
                       username=session['username'],
                       strand=session['strand'],
                       quizzes=strand_quizzes,
                       categories=get_strand_categories(strand),
                       user_completed_quizzes=user_completed_quizzes)

@app.route('/update_username', methods=['POST'])
def update_username():
    if 'user_email' not in session:
        return redirect(url_for('index'))

    new_username = request.form.get('new_username')
    if not new_username or len(new_username) < 3:
        flash('Username must be at least 3 characters long', 'error')
        return redirect(url_for('dashboard'))

    users = load_users()
    users[session['user_email']]['username'] = new_username
    session['username'] = new_username
    save_users(users)

    flash('Username updated successfully', 'success')
    return redirect(url_for('dashboard'))

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_email' not in session:
        return redirect(url_for('index'))

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not all([current_password, new_password, confirm_password]):
        flash('All fields are required', 'error')
        return redirect(url_for('dashboard'))

    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('dashboard'))

    if len(new_password) < 6:
        flash('Password must be at least 6 characters long', 'error')
        return redirect(url_for('dashboard'))

    users = load_users()
    user = users[session['user_email']]

    # Verify current password
    if not check_password_hash(user['password'], current_password):
        flash('Current password is incorrect', 'error')
        return redirect(url_for('dashboard'))

    # Update password
    user['password'] = generate_password_hash(new_password)
    save_users(users)

    flash('Password changed successfully', 'success')
    return redirect(url_for('dashboard'))

@app.route('/nimda/delete_quiz/<quiz_id>', methods=['POST'])
def admin_delete_quiz(quiz_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    quizzes = load_quizzes()
    quizzes = [quiz for quiz in quizzes if quiz['id'] != quiz_id]
    save_quizzes(quizzes)

    flash('Quiz deleted successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/start_quiz/<quiz_id>')
def start_quiz(quiz_id):
    if 'user_email' not in session:
        return redirect(url_for('index'))
    
    quizzes = load_quizzes()
    quiz = next((q for q in quizzes if q['id'] == quiz_id), None)
    
    if not quiz or 'questions' not in quiz:
        flash('Quiz not found or no questions available', 'error')
        return redirect(url_for('dashboard'))
    
    # Make sure time_per_question is set
    if 'time_per_question' not in quiz:
        quiz['time_per_question'] = 30
    
    return render_template('quiz.html', quiz=quiz)

@app.route('/submit-quiz', methods=['POST'])
def submit_quiz():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    
    quiz_id = request.form.get('quiz_id')
    quizzes = load_quizzes()
    
    # Find the quiz
    quiz = None
    for q in quizzes:
        if str(q.get('id')) == quiz_id:
            quiz = q
            break
    
    if not quiz:
        flash('Quiz not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Process answers
    score = 0
    total_questions = len(quiz.get('questions', []))
    answers = {}
    
    for i, question in enumerate(quiz.get('questions', [])):
        selected_answer = request.form.get(f'question_{i}')
        correct_answer = question.get('correct_answer')
        
        answers[f'question_{i}'] = {
            'question': question.get('question'),
            'selected_answer': selected_answer,
            'correct_answer': correct_answer,
            'is_correct': selected_answer == correct_answer
        }
        
        if selected_answer == correct_answer:
            score += 1
    
    # Calculate percentage
    percentage = round((score / total_questions) * 100) if total_questions > 0 else 0
    
    # Record quiz result
    users = load_users()
    user_email = session['user_email']
    
    if user_email in users:
        if 'quiz_history' not in users[user_email]:
            users[user_email]['quiz_history'] = []
        
        users[user_email]['quiz_history'].append({
            'quiz_id': quiz_id,
            'quiz_title': quiz.get('title'),
            'score': score,
            'total_questions': total_questions,
            'percentage': percentage,
            'timestamp': datetime.now().isoformat()
        })
        
        save_users(users)
    
    return render_template('quiz_results.html', 
                          quiz=quiz,
                          score=score,
                          total_questions=total_questions,
                          percentage=percentage,
                          answers=answers)

@app.route('/fail-quiz', methods=['POST'])
def fail_quiz():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    
    quiz_id = request.form.get('quiz_id')
    quizzes = load_quizzes()
    
    # Find the quiz
    quiz = None
    for q in quizzes:
        if str(q.get('id')) == quiz_id:
            quiz = q
            break
    
    if not quiz:
        flash('Quiz not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Record failed quiz result due to eye tracking violation
    users = load_users()
    user_email = session['user_email']
    
    if user_email in users:
        if 'quiz_history' not in users[user_email]:
            users[user_email]['quiz_history'] = []
        
        users[user_email]['quiz_history'].append({
            'quiz_id': quiz_id,
            'quiz_title': quiz.get('title'),
            'score': 0,
            'total_questions': len(quiz.get('questions', [])),
            'percentage': 0,
            'failed_reason': 'Eye tracking violation detected',
            'timestamp': datetime.now().isoformat()
        })
        
        save_users(users)
    
    flash('Quiz failed: Eye tracking violation detected. Your eyes were off screen for too long.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/api/check-eyes', methods=['POST'])
def check_eyes():
    if 'user_email' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get image data from POST request
        image_data = request.json.get('image', '')
        if not image_data or not image_data.startswith('data:image'):
            return jsonify({'error': 'Invalid image data'}), 400
        
        # Decode base64 image
        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        # Convert to OpenCV format
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Load face detector
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) == 0:
            return jsonify({'eyesOpen': False, 'reason': 'No face detected'})
        
        # Check for eyes in the face
        eyes_detected = False
        for (x, y, w, h) in faces:
            roi_gray = gray[y:y+h, x:x+w]
            eyes = eye_cascade.detectMultiScale(roi_gray)
            if len(eyes) >= 1:  # At least one eye detected
                eyes_detected = True
                break
        
        return jsonify({'eyesOpen': eyes_detected})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    title = request.form.get('quiz_title')
    description = request.form.get('quiz_description')
    category = request.form.get('quiz_category')
    strand = request.form.get('strand')
    topics = request.form.get('quiz_topics')
    time_per_question = request.form.get('time_per_question', 30)
    
    try:
        time_per_question = int(time_per_question)
        if time_per_question < 10:
            time_per_question = 10
        elif time_per_question > 300:
            time_per_question = 300
    except:
        time_per_question = 30
    
    if not all([title, description, category, strand, topics]):
        flash('Please fill in all fields', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Generate a unique ID for the quiz
    quiz_id = str(random.randint(10000, 99999))
    
    quiz = {
        'id': quiz_id,
        'title': title,
        'description': description,
        'category': category,
        'strand': strand,
        'topics': topics,
        'time_per_question': time_per_question,
        'created_at': datetime.now().isoformat()
    }
    
    quizzes = load_quizzes()
    quizzes.append(quiz)
    save_quizzes(quizzes)
    
    flash('Quiz created successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/nimda/get_quiz_questions/<quiz_id>')
def get_quiz_questions(quiz_id):
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
def admin_save_quiz_questions():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    quiz_id = request.form.get('quiz_id')
    question_texts = request.form.getlist('questions[]')
    
    # Find the quiz
    quizzes = load_quizzes()
    quiz = None
    for q in quizzes:
        if q['id'] == quiz_id:
            quiz = q
            break
    
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    # Process questions
    questions = []
    for i in range(len(question_texts)):
        # Get correct answer
        correct_answer = request.form.get(f'correct_answer_{i}')
        if not correct_answer:
            return jsonify({'error': f'Missing correct answer for question {i+1}'}), 400
        
        # Get time for this question
        time_per_question = request.form.get(f'time_per_question_{i}', 30)
        try:
            time_per_question = int(time_per_question)
            if time_per_question < 10:
                time_per_question = 10
            elif time_per_question > 300:
                time_per_question = 300
        except:
            time_per_question = 30
        
        # Get options
        options = []
        option_values = request.form.getlist(f'options_{i}[]')
        if option_values:
            options = option_values
        else:
            # Try alternate format
            for j in range(4):  # Assuming 4 options per question
                option = request.form.get(f'option_{j}_{i}')
                if option:
                    options.append(option)
        
        if len(options) < 2:
            return jsonify({'error': f'Not enough options for question {i+1}'}), 400
        
        # Create question object
        question = {
            'question': question_texts[i],
            'options': options,
            'correct_answer': int(correct_answer),
            'time_per_question': time_per_question
        }
        
        questions.append(question)
    
    # Update quiz with questions
    quiz['questions'] = questions
    
    # Calculate total quiz time (sum of all question times)
    total_time = sum(q['time_per_question'] for q in questions)
    quiz['total_time'] = total_time
    
    save_quizzes(quizzes)
    
    return jsonify({'success': True}), 200

@app.route('/get_categories/<strand>')
def get_categories(strand):
    categories = get_strand_categories(strand)
    return {'categories': categories}

@app.route('/account_settings')
def account_settings():
    if 'user_email' not in session:
        return redirect(url_for('index'))

    users = load_users()
    user = users[session['user_email']]

    # Get account creation date
    account_created = user.get('created_at', None)
    if account_created:
        try:
            account_created = datetime.fromisoformat(account_created).strftime('%B %d, %Y')
        except:
            account_created = 'N/A'

    # Get number of completed quizzes
    user_quiz_history = user.get('quiz_history', [])
    completed_quizzes = len(user_quiz_history)

    return render_template('account_settings.html',
                          username=session['username'],
                          strand=session['strand'],
                          account_created=account_created,
                          completed_quizzes=completed_quizzes)

@app.route('/update_account', methods=['POST'])
def update_account():
    if 'user_email' not in session:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Not logged in'})
        return redirect(url_for('index'))

    new_username = request.form.get('username')
    if not new_username or len(new_username) < 3:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Username must be at least 3 characters long'})
        flash('Username must be at least 3 characters long', 'error')
        return redirect(url_for('account_settings'))

    users = load_users()
    users[session['user_email']]['username'] = new_username
    session['username'] = new_username
    save_users(users)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Account updated successfully'})

    flash('Account updated successfully', 'success')
    return redirect(url_for('account_settings'))

@app.route('/delete_account')
def delete_account():
    if 'user_email' not in session:
        return redirect(url_for('index'))

    users = load_users()
    if session['user_email'] in users:
        del users[session['user_email']]
        save_users(users)

    session.clear()
    flash('Your account has been deleted', 'success')
    return redirect(url_for('index'))

@app.route('/get_ai_response', methods=['POST'])
def get_ai_response():
    if 'user_email' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})

    try:
        data = request.json
        user_message = data.get('message', '')
        chat_history = data.get('history', [])

        # Prepare the API request
        api_url = "https://api.deepseek.com/chat/completions"  # Updated to use the base URL without v1

        # Format messages for the API
        messages = chat_history

        # Add user context information
        system_message = f"You are a helpful AI assistant for students. The current user is {session['username']}, who is studying {session['strand']}. Provide concise, accurate information about academic subjects, study tips, and educational resources. Be friendly and supportive."

        # Update or add system message
        if messages and messages[0]['role'] == 'system':
            messages[0]['content'] = system_message
        else:
            messages.insert(0, {"role": "system", "content": system_message})

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }

        payload = {
            "model": "deepseek-chat",  # This will use DeepSeek-V3
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": False  # Explicitly set to false for non-streaming response
        }

        # Make the API request
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)

        # Check for HTTP errors
        if response.status_code != 200:
            error_message = f"API request failed with status code {response.status_code}"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_message = f"API Error: {error_data['error'].get('message', 'Unknown error')}"
            except:
                pass
            return jsonify({'success': False, 'error': error_message})

        response_data = response.json()

        # Extract the AI's response
        if 'choices' in response_data and len(response_data['choices']) > 0:
            ai_response = response_data['choices'][0]['message']['content']
            return jsonify({'success': True, 'response': ai_response})
        else:
            return jsonify({'success': False, 'error': 'Invalid API response', 'details': response_data})

    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': 'Request to DeepSeek API timed out. Please try again later.'})
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'error': 'Could not connect to DeepSeek API. Please check your internet connection.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

init_files()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key.pem'), debug=True)