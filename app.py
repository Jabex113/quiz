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
    if 'admin_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    quiz_id = request.form.get('quiz_id')
    questions = []

    # Process form data
    form_data = request.form.to_dict(flat=False)

    # Get all question texts
    question_texts = form_data.get('questions[]', [])

    # Process each question
    for i, question_text in enumerate(question_texts):
        # Get options for this question
        options_key = f'options_{i}[]'
        options = form_data.get(options_key, [])

        # Get correct answer
        correct_key = f'correct_answer_{i}'
        correct_answer = int(request.form.get(correct_key, 0))

        question = {
            'question': question_text,
            'options': options,
            'correct_answer': correct_answer
        }

        questions.append(question)

    quizzes = load_quizzes()
    for quiz in quizzes:
        if quiz['id'] == quiz_id:
            quiz['questions'] = questions
            break

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
    port = int(os.environ
    .get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)