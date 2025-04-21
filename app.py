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
import io
import uuid
import pymysql  # Add MySQL connector

# Add a custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')
app.json_encoder = DateTimeEncoder  # Use our custom JSON encoder for all JSON serialization

# Database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'quiz_app')

# Database connection function
def get_db_connection():
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        print("Using file-based storage as fallback")
        return None

# Register custom filters
@app.template_filter('datetime')
def format_datetime(value, format='%B %d, %Y at %I:%M %p'):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime(format)

EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

# DeepSeek API key - load from environment variable or use default for development
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', "sk-289d0e34995441d9b01e878fbaa61e2b")

# Legacy file-based storage (will be deprecated)
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

# Database user management functions
def get_user_by_email(email):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            return user
    finally:
        conn.close()

def create_user(username, fullname, lrn, email, password, strand):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            cursor.execute(
                "INSERT INTO users (username, fullname, lrn, email, password, strand) VALUES (%s, %s, %s, %s, %s, %s)",
                (username, fullname, lrn, email, hashed_password, strand)
            )
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()

def update_user(email, data):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Build update query dynamically based on provided data
            fields = []
            values = []
            for key, value in data.items():
                fields.append(f"{key} = %s")
                values.append(value)
            
            if not fields:
                return False
                
            values.append(email)  # For the WHERE clause
            query = f"UPDATE users SET {', '.join(fields)} WHERE email = %s"
            cursor.execute(query, values)
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()

def delete_user(email):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE email = %s", (email,))
        conn.commit()
        return True
    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()

# Legacy file functions (can be deprecated once migration is complete)
def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2, cls=DateTimeEncoder)

def load_stories():
    try:
        with open(STORIES_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_stories(stories):
    with open(STORIES_FILE, 'w') as f:
        json.dump(stories, f, indent=2, cls=DateTimeEncoder)

def load_quizzes():
    try:
        with open(QUIZZES_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_quizzes(quizzes):
    with open(QUIZZES_FILE, 'w') as f:
        json.dump(quizzes, f, indent=2, cls=DateTimeEncoder)

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
    fullname = request.form.get('fullname')
    lrn = request.form.get('lrn')
    email = request.form.get('email')
    password = request.form.get('password')
    strand = request.form.get('strand')
    
    if not all([username, fullname, lrn, email, password, strand]):
        flash('Please fill in all fields', 'error')
        return redirect(url_for('index'))

    # Check if user already exists in database
    existing_user = get_user_by_email(email)
    if existing_user:
        flash('Email already registered', 'error')
        return redirect(url_for('index'))

    otp = generate_otp()
    session['signup_data'] = {
        'username': username,
        'fullname': fullname,
        'lrn': lrn,
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

    # Create user in the database
    if not create_user(
        signup_data['username'],
        signup_data['fullname'],
        signup_data['lrn'],
        signup_data['email'],
        signup_data['password'],
        signup_data['strand']
    ):
        flash('Error creating account, please try again', 'error')
        return redirect(url_for('index'))

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

    # Get user from database
    user = get_user_by_email(email)
    if not user:
        flash('Invalid email or password', 'error')
        return redirect(url_for('index'))

    # Check if this is a teacher account
    if user.get('role') == 'teacher':
        flash('Teacher accounts must log in through the admin panel', 'error')
        return redirect(url_for('index'))

    if not check_password_hash(user['password'], password):
        flash('Invalid email or password', 'error')
        return redirect(url_for('index'))

    session['user_email'] = email
    session['username'] = user['username']
    session['strand'] = user.get('strand', '')
    
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session:
        flash('Please log in to access your dashboard', 'error')
        return redirect(url_for('index'))
    
    # Get user information from database or file
    user = get_user_by_email(session['user_email'])
    if not user:
        # Try from legacy file storage
        users = load_users()
        user = users.get(session['user_email'])
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('index'))
    
    # Display one-time notification about quiz policy (only if from start_quiz redirect)
    if request.args.get('source') == 'quiz_policy':
        flash('Remember: Each quiz can only be taken once. Complete each quiz carefully!', 'info')
    
    # Load quizzes
    quizzes = load_quizzes()
    
    # Get quiz attempts from database for this user
    quiz_stats = {}
    total_completed_quizzes = 0
    
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # Get all user quiz attempts
                cursor.execute(
                    """SELECT quiz_id, score, raw_score, total_questions, passed FROM quiz_attempts 
                       WHERE user_id = %s""",
                    (user.get('id', 0))
                )
                attempts = cursor.fetchall()
                
                # Count total completed quizzes
                total_completed_quizzes = len(attempts)
                
                # Group attempts by quiz_id to find highest score for each quiz
                for attempt in attempts:
                    quiz_id = attempt['quiz_id']
                    score_percentage = attempt['score']
                    raw_score = attempt.get('raw_score', 0)  # Default to 0 if field doesn't exist
                    total_questions = attempt.get('total_questions', 10)  # Default to 10 if field doesn't exist
                    passed = attempt['passed']
                    
                    if quiz_id not in quiz_stats or score_percentage > quiz_stats[quiz_id].get('score_percentage', 0):
                        quiz_stats[quiz_id] = {
                            'score_percentage': score_percentage,
                            'raw_score': raw_score,
                            'total_questions': total_questions,
                            'passed': passed
                        }
            conn.close()
        else:
            # Fallback to file-based quiz history if database not available
            quiz_history = user.get('quiz_history', [])
            total_completed_quizzes = len(quiz_history)
            
            # Extract stats from quiz history
            for attempt in quiz_history:
                quiz_id = attempt.get('quiz_id')
                score_percentage = attempt.get('score_percentage', attempt.get('score', 0))
                raw_score = attempt.get('raw_score', 0)
                total_questions = attempt.get('total_score', attempt.get('total_questions', 10))
                passed = score_percentage >= 60  # Assuming 60% is passing
                
                if quiz_id not in quiz_stats or score_percentage > quiz_stats[quiz_id].get('score_percentage', 0):
                    quiz_stats[quiz_id] = {
                        'score_percentage': score_percentage,
                        'raw_score': raw_score,
                        'total_questions': total_questions,
                        'passed': passed
                    }
    except Exception as e:
        print(f"Error fetching quiz attempts: {e}")
        # Fallback to file-based quiz history
        if isinstance(user, dict):
            quiz_history = user.get('quiz_history', [])
            total_completed_quizzes = len(quiz_history)
    
    # Add question_count to each quiz
    for quiz in quizzes:
        quiz['question_count'] = len(quiz.get('questions', []))
    
    return render_template('dashboard.html', 
        user=user,
        quizzes=quizzes,
        total_completed_quizzes=total_completed_quizzes,
        quiz_stats=quiz_stats
    )

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
def delete_quiz(quiz_id):
    if 'admin_logged_in' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    quizzes = load_quizzes()
    quizzes = [q for q in quizzes if q['id'] != quiz_id]
    save_quizzes(quizzes)
    
    return jsonify({"success": True})

@app.route('/nimda/reset_quiz/<quiz_id>', methods=['POST'])
def reset_quiz(quiz_id):
    if 'admin_logged_in' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # Load user data
        users = load_users()
        
        # For each user, remove the specified quiz from their quiz history
        for email, user_data in users.items():
            if 'quiz_history' in user_data:
                # Filter out the quiz with the given quiz_id
                user_data['quiz_history'] = [
                    quiz_result for quiz_result in user_data['quiz_history'] 
                    if quiz_result.get('quiz_id') != quiz_id
                ]
        
        # Save the updated user data
        save_users(users)
        
        return jsonify({"success": True, "message": "Quiz reset successful. Students can now retake it."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/start_quiz/<quiz_id>')
def start_quiz(quiz_id):
    if 'user_email' not in session:
        return redirect(url_for('index'))
    
    # Get user information
    user = get_user_by_email(session['user_email'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if the user has already completed this quiz
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM quiz_attempts WHERE user_id = %s AND quiz_id = %s", 
                (user['id'], quiz_id)
            )
            existing_attempt = cursor.fetchone()
            if existing_attempt:
                flash('You have already taken this quiz. Each quiz can only be taken once.', 'error')
                return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"Error checking quiz attempts: {e}")
        # Fall back to file-based check for legacy users
        if isinstance(user, dict) and 'quiz_history' in user:
            for attempt in user['quiz_history']:
                if attempt.get('quiz_id') == quiz_id:
                    flash('You have already taken this quiz. Each quiz can only be taken once.', 'error')
                    return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()
    
    # Let's remind users of the one-attempt policy when they first access a quiz
    if request.args.get('confirm') != 'yes':
        flash('Important: You can only take each quiz ONCE. Are you ready to begin?', 'warning')
        return redirect(url_for('dashboard', source='quiz_policy'))
    
    quizzes = load_quizzes()
    quiz = next((q for q in quizzes if q['id'] == quiz_id), None)
    
    # Debug: print quiz details
    print("\n===== QUIZ DEBUG INFO =====")
    print(f"Quiz ID: {quiz_id}")
    print(f"Quiz found: {quiz is not None}")
    if quiz:
        print(f"Quiz title: {quiz.get('title', 'No title')}")
        print(f"Questions count: {len(quiz.get('questions', []))}")
        if 'questions' in quiz and len(quiz['questions']) > 0:
            print(f"First question: {quiz['questions'][0].get('question', 'No question text')}")
        else:
            print("No questions found in quiz")
    print("===========================\n")
    
    if not quiz or 'questions' not in quiz:
        flash('Quiz not found or no questions available', 'error')
        return redirect(url_for('dashboard'))
    
    # Make sure all questions have time limits set and standardized field names
    for question in quiz['questions']:
        # Set default time if neither field exists
        if 'time_per_question' not in question and 'time_limit' not in question:
            question['time_per_question'] = 30  # Default 30 seconds if not set
        # If only time_limit exists, copy to time_per_question for consistency
        elif 'time_limit' in question and 'time_per_question' not in question:
            question['time_per_question'] = question['time_limit'] 
        # If only time_per_question exists, copy to time_limit for backward compatibility
        elif 'time_per_question' in question and 'time_limit' not in question:
            question['time_limit'] = question['time_per_question']
    
    # Calculate and set total quiz time if not already set
    if 'total_time' not in quiz:
        quiz['total_time'] = sum(q.get('time_per_question', 30) for q in quiz['questions'])
    
    return render_template('quiz.html', quiz=quiz)

def create_tables(cursor):
    """Create all required tables if they don't exist"""
    
    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) NOT NULL UNIQUE,
        username VARCHAR(100) NOT NULL,
        fullname VARCHAR(255) NOT NULL,
        lrn VARCHAR(50) NOT NULL,
        password VARCHAR(255) NOT NULL,
        strand VARCHAR(50) NOT NULL,
        role ENUM('student', 'teacher', 'admin') DEFAULT 'student',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create quizzes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quizzes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        category VARCHAR(100) NOT NULL,
        strand VARCHAR(50) NOT NULL,
        created_by VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        time_limit INT DEFAULT 0,
        passing_score INT DEFAULT 60
    )
    """)
    
    # Create questions table - with updated question types
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiz_questions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        quiz_id INT NOT NULL,
        question TEXT NOT NULL,
        question_type ENUM('multiple_choice', 'true_false', 'short_answer', 'fill_blank', 'matching') NOT NULL,
        options JSON,
        correct_answer TEXT,
        points INT DEFAULT 1,
        FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
    )
    """)
    
    # Create quiz attempts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiz_attempts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        quiz_id VARCHAR(255) NOT NULL,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
        score DECIMAL(5,2) DEFAULT 0,
        raw_score INT DEFAULT 0,
        total_questions INT DEFAULT 0,
        passed BOOLEAN DEFAULT FALSE,
        answers JSON,
        INDEX (user_id),
        INDEX (quiz_id)
    )
    """)
    
    # Create mapping table between UUID and database IDs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiz_id_mapping (
        id INT AUTO_INCREMENT PRIMARY KEY,
        uuid VARCHAR(255) NOT NULL UNIQUE,
        db_id INT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX (uuid),
        INDEX (db_id)
    )
    """)
    
    # Check if raw_score and total_questions columns exist in quiz_attempts, add if not
    try:
        cursor.execute("SHOW COLUMNS FROM quiz_attempts LIKE 'raw_score'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE quiz_attempts ADD COLUMN raw_score INT DEFAULT 0")
            print("Added raw_score column to quiz_attempts table")
    
        cursor.execute("SHOW COLUMNS FROM quiz_attempts LIKE 'total_questions'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE quiz_attempts ADD COLUMN total_questions INT DEFAULT 0")
            print("Added total_questions column to quiz_attempts table")
    except Exception as e:
        print(f"Error checking or adding columns: {e}")

# Make sure tables exist when app starts
try:
    conn = get_db_connection()
    if conn:
        with conn.cursor() as cursor:
            create_tables(cursor)
        conn.commit()
        conn.close()
    else:
        print("Skipping table creation - using file-based storage")
except Exception as e:
    print(f"Error creating tables: {e}")
    print("Continuing with file-based storage")

# Initialize files
init_files()

@app.route('/submit-quiz', methods=['POST'])
def submit_quiz():
    if 'user_email' not in session:
        flash('Please log in to take quizzes', 'error')
        return redirect(url_for('index'))
    
    quiz_id = request.form.get('quiz_id')
    timeout = request.form.get('timeout') == 'true'
    
    quizzes = load_quizzes()
    quiz = None
    
    for q in quizzes:
        if q['id'] == quiz_id:
            quiz = q
            break
    
    if not quiz:
        flash('Quiz not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Get user information
    user = get_user_by_email(session['user_email'])
    if not user:
        # Try file-based storage
        users = load_users()
        user = users.get(session['user_email'])
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('dashboard'))
    
    # Initialize results
    correct_count = 0
    total_questions = len(quiz.get('questions', []))
    question_results = []
    
    # Process each question based on type
    for i, question in enumerate(quiz.get('questions', [])):
        question_type = question.get('question_type', 'multiple_choice')
        user_answer = None
        is_correct = False
        feedback = ""
        
        # Get user's answer based on question type
        if question_type == 'multiple_choice':
            user_answer = request.form.get(f'answer_{i}')
            if user_answer is not None:
                try:
                    user_answer = int(user_answer)
                    correct_answer = question.get('correct_answer')
                    is_correct = user_answer == correct_answer
                except (ValueError, TypeError):
                    pass
        
        elif question_type == 'true_false':
            user_answer = request.form.get(f'answer_{i}')
            correct_answer = question.get('correct_answer')
            is_correct = user_answer == correct_answer if user_answer is not None and correct_answer is not None else False
        
        elif question_type == 'short_answer':
            user_answer_raw = request.form.get(f'answer_{i}', '')
            user_answer = user_answer_raw.strip() if user_answer_raw is not None else ''
            
            correct_answer_raw = question.get('correct_answer', '')
            correct_answer = correct_answer_raw.strip() if correct_answer_raw is not None else ''
            
            # Case-insensitive comparison
            is_correct = user_answer.lower() == correct_answer.lower() if user_answer and correct_answer else False
            
            # If not matched exactly, check if it contains the main keywords
            if not is_correct and user_answer and correct_answer:
                # Split both answers into words and check if all important words from correct answer
                # are present in user's answer
                correct_words = set(w.lower() for w in correct_answer.split() if len(w) > 3)
                user_words = set(w.lower() for w in user_answer.split())
                
                # If the user has included at least 80% of the important words, consider it correct
                if correct_words and len(correct_words.intersection(user_words)) / len(correct_words) >= 0.8:
                    is_correct = True
                    feedback = "Partially correct but accepted."
        
        elif question_type == 'fill_blank':
            user_answer_raw = request.form.get(f'answer_{i}', '')
            user_answer = user_answer_raw.strip() if user_answer_raw is not None else ''
            
            correct_answer_raw = question.get('correct_answer', '')
            correct_answer = correct_answer_raw.strip() if correct_answer_raw is not None else ''
            
            # Case-insensitive comparison
            is_correct = user_answer.lower() == correct_answer.lower() if user_answer and correct_answer else False
            
            # If not matched exactly, check similarity
            if not is_correct and user_answer and correct_answer:
                # If the answers are similar length and share most of the same characters
                if abs(len(user_answer) - len(correct_answer)) <= 2:
                    user_chars = set(user_answer.lower())
                    correct_chars = set(correct_answer.lower())
                    if len(user_chars.intersection(correct_chars)) / len(correct_chars) >= 0.8:
                        is_correct = True
                        feedback = "Partially correct but accepted."
        
        elif question_type == 'matching':
            # Get all selected options for this matching question
            user_answers = {}
            for key, value in request.form.items():
                if key.startswith(f'match_{i}_'):
                    item_index = key.split('_')[2]
                    user_answers[item_index] = value
            
            user_answer = user_answers
            
            # Check if all matching items are correct
            is_correct = True
            matching_pairs = question.get('matching_pairs', [])
            if not matching_pairs:  # If no matching pairs, can't be correct
                is_correct = False
            else:
                for item_index, selected_value in user_answers.items():
                    try:
                        item_idx = int(item_index)
                        if item_idx < len(matching_pairs):
                            correct_value = matching_pairs[item_idx].get('match')
                            if selected_value != correct_value:
                                is_correct = False
                                break
                        else:
                            is_correct = False
                            break
                    except (ValueError, TypeError, IndexError):
                        is_correct = False
                        break
        
        # Add to correct count if answer is correct
        if is_correct:
            correct_count += 1
        
        # Store the result for this question
        question_results.append({
            'question': question.get('question', ''),
            'question_type': question_type,
            'user_answer': user_answer,
            'correct_answer': question.get('correct_answer'),
            'is_correct': is_correct,
            'feedback': feedback
        })
    
    # Calculate score as number of correct answers and percentage
    raw_score = correct_count
    total_score = total_questions
    score_percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0
    
    # Store in file-based system
    if isinstance(user, dict):
        if 'quiz_history' not in user:
            user['quiz_history'] = []
        
        user['quiz_history'].append({
            'quiz_id': quiz_id,
            'quiz_title': quiz.get('title', ''),
            'timestamp': datetime.now(),
            'raw_score': raw_score,
            'total_score': total_score,
            'score_percentage': score_percentage,
            'question_results': question_results,
            'timeout': timeout
        })
        
        # Save to file system
        users = load_users()
        users[session['user_email']] = user
        save_users(users)
    
    # Try to record the quiz attempt in the database
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                # Insert quiz attempt - using direct string for quiz_id since it may not be an integer
                cursor.execute(
                    """INSERT INTO quiz_attempts 
                       (user_id, quiz_id, score, raw_score, total_questions, passed, answers) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        user.get('id', 0),
                        quiz_id,
                        score_percentage,
                        raw_score,
                        total_questions,
                        score_percentage >= quiz.get('passing_score', 60),
                        json.dumps(question_results, cls=DateTimeEncoder)
                    )
                )
                print(f"Successfully inserted quiz attempt with ID: {cursor.lastrowid}")
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"Error recording quiz attempt in database: {e}")
    
    # Create quiz result record - use datetime directly since we have a custom encoder
    result = {
        'quiz_id': quiz_id,
        'quiz_title': quiz.get('title', ''),
        'timestamp': datetime.now(),
        'raw_score': raw_score,
        'total_score': total_score,
        'score_percentage': score_percentage,
        'question_results': question_results,
        'timeout': timeout
    }
    
    # Store the result in the session for display on the results page
    session['last_quiz_results'] = result
    
    # Redirect to results page
    return redirect(url_for('quiz_results', quiz_id=quiz_id, score=f"{raw_score}/{total_score}"))

@app.route('/quiz-results')
def quiz_results():
    if 'user_email' not in session:
        flash('Please log in to view quiz results', 'error')
        return redirect(url_for('index'))
    
    if 'last_quiz_results' not in session:
        flash('No quiz results found', 'error')
        return redirect(url_for('dashboard'))
    
    results = session['last_quiz_results']
    return render_template('quiz_results.html', results=results)

def check_ai_content(text):
    """
    Check if text appears to be AI-generated.
    Returns a score between 0 and 1 where higher values indicate
    more likely AI-generated content.
    """
    # Simple placeholder implementation
    return 0  # Always return 0 (no AI content detected)

def check_plagiarism(text):
    """
    Check if text appears to be plagiarized.
    Returns a score between 0 and 1 where higher values indicate
    more likely plagiarism.
    
    Note: This is a simplified implementation. A real implementation
    would use a plagiarism detection service.
    """
    # Simplified implementation - in a real app, use a service like Turnitin
    # For now, just return a random score for demo purposes
    try:
        # Simulate a plagiarism check with random value
        # In a real implementation, integrate with a plagiarism detection service
        plagiarism_score = random.uniform(0, 0.3)  # For demo, low random scores
        
        return plagiarism_score
    except Exception as e:
        print(f"Error checking plagiarism: {e}")
        return 0  # Default to no plagiarism on error

@app.route('/fail-quiz', methods=['GET', 'POST'])
def fail_quiz():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    
    # Get quiz_id and reason from either URL parameters (GET) or form data (POST)
    if request.method == 'POST':
        quiz_id = request.form.get('quiz_id')
        reason = request.form.get('reason', 'unknown')
    else:  # GET request
        quiz_id = request.args.get('quiz_id')
        reason = request.args.get('reason', 'unknown')
    
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
    
    # Get user information
    user = get_user_by_email(session['user_email'])
    
    # Record failure in database if possible
    if user and 'id' in user:
        try:
            conn = get_db_connection()
            if conn:
                with conn.cursor() as cursor:
                    # Insert quiz attempt with score 0
                    cursor.execute(
                        """INSERT INTO quiz_attempts 
                           (user_id, quiz_id, score, passed, answers) 
                           VALUES (%s, %s, %s, %s, %s)""",
                        (
                            user['id'],
                            quiz_id,
                            0,  # score is 0 for failed quiz
                            False,  # not passed
                            json.dumps([{
                                'question': 'Quiz failed',
                                'question_type': 'system',
                                'reason': 'Timeout' if reason == 'timeout' else 'Eye tracking violation detected',
                                'is_correct': False
                            }], cls=DateTimeEncoder)
                        )
                    )
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"Error recording failed quiz in database: {e}")
    
    # Record failed quiz result in file-based system as fallback
    users = load_users()
    user_email = session['user_email']
    
    if user_email in users:
        if 'quiz_history' not in users[user_email]:
            users[user_email]['quiz_history'] = []
        
        # Use datetime directly since we have a custom encoder
        users[user_email]['quiz_history'].append({
            'quiz_id': quiz_id,
            'quiz_title': quiz.get('title'),
            'score': 0,
            'total_questions': len(quiz.get('questions', [])),
            'percentage': 0,
            'failed_reason': 'Timeout' if reason == 'timeout' else 'Eye tracking violation detected',
            'timestamp': datetime.now()
        })
        
        save_users(users)
    
    if reason == 'timeout':
        flash('Quiz failed: Time limit exceeded.', 'error')
    else:
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
            return jsonify({
                'eyesOpen': False, 
                'reason': 'No face detected',
                'warning': True,
                'message': 'Face not visible - please stay in frame'
            })
        
        # Check for eyes in the face
        eyes_detected = False
        for (x, y, w, h) in faces:
            roi_gray = gray[y:y+h, x:x+w]
            eyes = eye_cascade.detectMultiScale(roi_gray)
            if len(eyes) >= 1:  # At least one eye detected
                eyes_detected = True
                break
        
        if not eyes_detected:
            return jsonify({
                'eyesOpen': False,
                'reason': 'Eyes not detected',
                'warning': True,
                'message': 'Eyes not visible - please face the screen'
            })
        
        return jsonify({
            'eyesOpen': True,
            'reason': 'Eyes detected'
        })
    
    except Exception as e:
        print(f"Error in eye detection: {str(e)}")
        return jsonify({'error': str(e), 'eyesOpen': True}), 200  # Return 200 to avoid interrupting quiz

@app.route('/logout')
def logout():
    if 'user_email' in session:
        session.pop('user_email')
    if 'username' in session:
        session.pop('username')
    if 'strand' in session:
        session.pop('strand')
    return redirect(url_for('index'))

@app.route('/nimda/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Admin login
        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            session['is_teacher'] = False
            flash('Admin login successful', 'success')
            return redirect(url_for('admin_dashboard'))
            
        # Teacher login - check database
        email = username  # Use username field for email
        user = get_user_by_email(email)
        
        if user and user.get('role') == 'teacher' and check_password_hash(user['password'], password):
            session['admin_logged_in'] = True
            session['is_teacher'] = True
            session['user_email'] = email
            session['username'] = user['username']
            flash('Teacher login successful', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin/teacher credentials', 'error')
    
    return render_template('nimda/admin_login.html')

@app.route('/nimda/dashboard')
def admin_dashboard():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    is_teacher = session.get('is_teacher', False)
    
    # Get all users and quizzes
    users = load_users()
    quizzes = load_quizzes()
    
    return render_template('nimda/admin_dashboard.html', users=users, quizzes=quizzes, is_teacher=is_teacher)

@app.route('/nimda/post_quiz', methods=['POST'])
def admin_post_quiz():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    try:
        quiz_title = request.form.get('quiz_title')
        quiz_description = request.form.get('quiz_description')
        quiz_topics = request.form.get('quiz_topics')
        strand = request.form.get('strand')
        author_first_name = request.form.get('author_first_name', '')
        author_last_name = request.form.get('author_last_name', '')
        grade_level = request.form.get('grade_level', '')
        quiz_category = request.form.get('quiz_category', '')
        
        if not all([quiz_title, quiz_description, quiz_topics, strand]):
            flash('Please fill in all required fields', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Generate UUID for the quiz
        quiz_id = str(uuid.uuid4())
        
        # Create new quiz
        new_quiz = {
            'id': quiz_id,
            'title': quiz_title,
            'description': quiz_description,
            'topics': quiz_topics,
            'strand': strand,
            'created_at': datetime.now().isoformat(),
            'questions': [],
            'author_first_name': author_first_name,
            'author_last_name': author_last_name,
            'grade_level': grade_level,
            'quiz_category': quiz_category
        }
        
        # Add to file storage
        quizzes = load_quizzes()
        quizzes.append(new_quiz)
        save_quizzes(quizzes)
        
        # Also add to database
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                # Insert new quiz into database
                cursor.execute(
                    """INSERT INTO quizzes 
                       (title, description, category, strand, created_by, created_at) 
                       VALUES (%s, %s, %s, %s, %s, NOW())""",
                    (
                        quiz_title,
                        quiz_description,
                        quiz_category,
                        strand,
                        'admin',
                    )
                )
                db_quiz_id = cursor.lastrowid
                
                # Create a mapping from UUID to database ID to help with quiz questions later
                cursor.execute(
                    """INSERT INTO quiz_id_mapping (uuid, db_id) VALUES (%s, %s)""",
                    (quiz_id, db_quiz_id)
                )
                
                print(f"Created new quiz in database with ID: {db_quiz_id}, UUID: {quiz_id}")
            conn.commit()
        except Exception as e:
            print(f"Error adding quiz to database: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()
        
        flash('Quiz created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f'Error creating quiz: {str(e)}', 'error')
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
        return jsonify({"error": "Unauthorized"}), 401

    # Debug logging
    print("\n===== SAVE QUIZ QUESTIONS DEBUG =====")
    
    quiz_id = request.form.get('quiz_id')
    print(f"Quiz ID (UUID): {quiz_id}")
    
    questions_text = request.form.getlist('questions[]')
    print(f"Number of questions: {len(questions_text)}")
    
    question_indices = request.form.getlist('question_index[]')
    print(f"Question indices: {question_indices}")
    
    question_types = request.form.getlist('question_types[]')
    print(f"Question types: {question_types}")
    
    time_per_question = []
    total_time = 0
    
    quizzes = load_quizzes()
    quiz = None
    
    for q in quizzes:
        if q['id'] == quiz_id:
            quiz = q
            break
    
    if not quiz:
        print("ERROR: Quiz not found!")
        return jsonify({"error": "Quiz not found"}), 404
    
    # Initialize questions array
    quiz['questions'] = []
    print(f"Reset quiz questions array to empty")
    
    # Store database quiz ID if it exists
    db_quiz_id = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # First check the mapping table
            cursor.execute("SELECT db_id FROM quiz_id_mapping WHERE uuid = %s", (quiz_id,))
            mapping = cursor.fetchone()
            
            if mapping:
                db_quiz_id = mapping['db_id']
                print(f"Found quiz in mapping table with DB ID: {db_quiz_id}")
                
                # Delete existing questions for this quiz
                cursor.execute("DELETE FROM quiz_questions WHERE quiz_id = %s", (db_quiz_id,))
                print(f"Deleted existing questions for quiz ID: {db_quiz_id}")
            else:
                # Check if quiz exists in database by ID
                cursor.execute("SELECT id FROM quizzes WHERE id = %s", (quiz_id,))
                result = cursor.fetchone()
                
                if result:
                    db_quiz_id = result['id']
                    print(f"Found quiz directly in database with ID: {db_quiz_id}")
                    
                    # Add to mapping for future lookups
                    cursor.execute(
                        "INSERT INTO quiz_id_mapping (uuid, db_id) VALUES (%s, %s)",
                        (quiz_id, db_quiz_id)
                    )
                    
                    # Delete existing questions
                    cursor.execute("DELETE FROM quiz_questions WHERE quiz_id = %s", (db_quiz_id,))
                    print(f"Deleted existing questions for quiz ID: {db_quiz_id}")
                else:
                    # Need to create the quiz in database
                    cursor.execute(
                        """INSERT INTO quizzes 
                           (title, description, category, strand, created_by, created_at) 
                           VALUES (%s, %s, %s, %s, %s, NOW())""",
                        (
                            quiz.get('title', ''),
                            quiz.get('description', ''),
                            quiz.get('quiz_category', ''),
                            quiz.get('strand', ''),
                            'admin',
                        )
                    )
                    db_quiz_id = cursor.lastrowid
                    print(f"Created new quiz in database with ID: {db_quiz_id}")
                    
                    # Add to mapping
                    cursor.execute(
                        "INSERT INTO quiz_id_mapping (uuid, db_id) VALUES (%s, %s)",
                        (quiz_id, db_quiz_id)
                    )
        
        conn.commit()
    except Exception as e:
        print(f"Error accessing quiz in database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
    
    # Process each question based on its type
    db_questions = []  # To store questions for database insertion
    
    for idx, q_idx in enumerate(question_indices):
        q_idx = int(q_idx)
        question_text = questions_text[idx]
        question_type = question_types[idx]
        time_limit = int(request.form.get(f'time_limit_{q_idx}', 30))
        
        print(f"\nProcessing question {idx+1}: {question_text[:30]}...")
        print(f"  Type: {question_type}, Time limit: {time_limit}")
        
        # Common question attributes
        question_data = {
            "question": question_text,
            "question_type": question_type,
            "time_per_question": time_limit
        }
        
        # Initialize database question data
        db_question = {
            'quiz_id': db_quiz_id,
            'question': question_text,
            'question_type': question_type,
            'options': None,
            'correct_answer': None
        }
        
        # Add type-specific data
        if question_type == "multiple_choice":
            options = request.form.getlist(f'options_{q_idx}[]')
            correct_answer = int(request.form.get(f'correct_answer_{q_idx}', 0))
            question_data["options"] = options
            question_data["correct_answer"] = correct_answer
            
            db_question["options"] = json.dumps(options, cls=DateTimeEncoder)
            db_question['correct_answer'] = str(correct_answer)
            
            print(f"  Multiple choice: {len(options)} options, correct: {correct_answer}")
            
        elif question_type == "true_false":
            correct_answer = request.form.get(f'tf_correct_answer_{q_idx}')
            question_data["correct_answer"] = correct_answer
            db_question['correct_answer'] = correct_answer
            print(f"  True/False: correct: {correct_answer}")
            
        elif question_type == "short_answer":
            correct_answer = request.form.get(f'short_answer_{q_idx}')
            question_data["correct_answer"] = correct_answer
            db_question['correct_answer'] = correct_answer
            question_data["ai_detection"] = request.form.get(f'ai_detection_{q_idx}') == 'on'
            print(f"  Short answer: correct: {correct_answer}, AI detection: {question_data['ai_detection']}")
            
        elif question_type == "fill_blank":
            blanks = request.form.getlist(f'fill_blank_answers_{q_idx}[]')
            question_data["blanks"] = blanks
            db_question['correct_answer'] = blanks[0] if blanks else ''
            db_question['options'] = json.dumps(blanks, cls=DateTimeEncoder)
            print(f"  Fill in blank: {len(blanks)} blanks")
            
        elif question_type == "matching":
            left_items = request.form.getlist(f'matching_left_{q_idx}[]')
            right_items = request.form.getlist(f'matching_right_{q_idx}[]')
            correct_matches = request.form.getlist(f'matching_pairs_{q_idx}[]')
            
            # Convert to integers for the matching pairs
            correct_matches = [int(m) for m in correct_matches]
            
            question_data["left_items"] = left_items
            question_data["right_items"] = right_items
            question_data["correct_matches"] = correct_matches
            
            # Store matching data in database format
            matching_data = {
                'left_items': left_items,
                'right_items': right_items,
                'correct_matches': correct_matches
            }
            db_question['options'] = json.dumps(matching_data, cls=DateTimeEncoder)
            db_question['correct_answer'] = json.dumps(correct_matches, cls=DateTimeEncoder)
            
            print(f"  Matching: {len(left_items)} left items, {len(right_items)} right items")
        
        # Add to questions list and track time
        quiz['questions'].append(question_data)
        db_questions.append(db_question)
        time_per_question.append(time_limit)
        total_time += time_limit
    
    # Update total time for the quiz
    quiz['total_time'] = total_time
    print(f"\nTotal quiz time: {total_time} seconds")
    
    # Add author information if provided
    author_first_name = request.form.get('author_first_name', '')
    author_last_name = request.form.get('author_last_name', '')
    if author_first_name or author_last_name:
        quiz['author'] = {
            'first_name': author_first_name,
            'last_name': author_last_name
        }
        print(f"Author: {author_first_name} {author_last_name}")
    
    # Add grade level if provided
    grade_level = request.form.get('grade_level', '')
    if grade_level:
        quiz['grade_level'] = grade_level
        print(f"Grade level: {grade_level}")
    
    # Save updated quizzes to file
    save_quizzes(quizzes)
    print(f"Saved quiz to file with {len(quiz['questions'])} questions")
    
    # Save questions to database
    if db_quiz_id:
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                for question in db_questions:
                    cursor.execute(
                        """INSERT INTO quiz_questions 
                           (quiz_id, question, question_type, options, correct_answer) 
                           VALUES (%s, %s, %s, %s, %s)""",
                        (
                            db_quiz_id,
                            question['question'],
                            question['question_type'],
                            question['options'],
                            question['correct_answer']
                        )
                    )
            conn.commit()
            print(f"Saved {len(db_questions)} questions to database for quiz ID: {db_quiz_id}")
        except Exception as e:
            print(f"Error saving questions to database: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()
    
    print("===== END SAVE QUIZ QUESTIONS DEBUG =====\n")
    
    # Verify the save worked by trying to load the file again
    verification_quizzes = load_quizzes()
    verification_quiz = next((q for q in verification_quizzes if q['id'] == quiz_id), None)
    if verification_quiz and 'questions' in verification_quiz:
        print(f"Verification: Quiz has {len(verification_quiz['questions'])} questions after saving")
    else:
        print("WARNING: Verification failed - quiz questions may not have been saved correctly")
    
    return jsonify({"success": True, "message": f"Saved {len(quiz['questions'])} questions"})

@app.route('/get_categories/<strand>')
def get_categories(strand):
    categories = get_strand_categories(strand)
    return {'categories': categories}

@app.route('/account_settings')
def account_settings():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    
    email = session['user_email']
    user = get_user_by_email(email)
    
    if not user:
        session.clear()
        return redirect(url_for('index'))
    
    # Get the number of completed quizzes
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM quiz_attempts WHERE user_id = %s", (user['id'],))
            result = cursor.fetchone()
            completed_quizzes = result['count'] if result else 0
    except pymysql.MySQLError as e:
        completed_quizzes = 0
    finally:
        conn.close()
    
    # Ensure created_at is a string
    created_at = user['created_at']
    if isinstance(created_at, datetime):
        created_at = created_at.strftime('%B %d, %Y at %I:%M %p')
    
    return render_template(
        'account_settings.html',
        username=user['username'],
        strand=user['strand'],
        account_created=created_at,
        completed_quizzes=completed_quizzes
    )

@app.route('/update_account', methods=['POST'])
def update_account():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Not logged in"})
    
    email = session['user_email']
    user = get_user_by_email(email)
    
    if not user:
        return jsonify({"success": False, "message": "User not found"})
    
    new_username = request.form.get('username')
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    
    data = {}
    
    if new_username and new_username != user['username']:
        data['username'] = new_username
        session['username'] = new_username
    
    if current_password and new_password:
        if not check_password_hash(user['password'], current_password):
            return jsonify({"success": False, "message": "Current password is incorrect"})
        
        data['password'] = generate_password_hash(new_password, method='pbkdf2:sha256')
    
    if data:
        if update_user(email, data):
            return jsonify({"success": True, "message": "Account updated successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to update account"})
    
    return jsonify({"success": True, "message": "No changes made"})

@app.route('/delete_account')
def delete_account():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    
    email = session['user_email']
    
    if delete_user(email):
        session.clear()
        flash('Your account has been deleted', 'success')
    else:
        flash('Failed to delete account', 'error')
    
    return redirect(url_for('index'))

@app.route('/get_ai_response', methods=['POST'])
def get_ai_response():
    if 'user_email' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})

    return jsonify({'success': False, 'error': 'AI assistant has been removed'})

@app.route('/nimda/create_teacher', methods=['POST'])
def create_teacher():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    
    if not all([username, email, password]):
        flash('Please fill in all fields', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Check if user already exists in database
    existing_user = get_user_by_email(email)
    if existing_user:
        flash('Email already registered', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Create teacher account in database
    if not create_user(
        username,
        '',  # fullname (not needed for teachers)
        '',  # lrn (not needed for teachers)
        email,
        password,
        '',  # strand (not needed for teachers)
    ):
        flash('Error creating teacher account', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Update the created user to set role as teacher
    update_user(email, {'role': 'teacher'})
    
    flash('Teacher account created successfully. Teacher can login through the admin panel using their email and password.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/nimda/logout')
def admin_logout():
    if 'admin_logged_in' in session:
        session.pop('admin_logged_in')
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=True)