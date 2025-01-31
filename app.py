from flask import Flask, request, render_template, session, redirect, url_for, flash
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
       return [
           {
               'id': '1',
               'title': 'Advanced Calculus',
               'description': 'Test your knowledge in differential equations and complex analysis',
               'topics': 'Derivatives,Integration,Series',
               'timestamp': datetime.now().isoformat()
           },
           {
               'id': '2',
               'title': 'Quantum Mechanics', 
               'description': 'Explore the fascinating world of quantum physics',
               'topics': 'Wave Functions,Uncertainty,Spin',
               'timestamp': datetime.now().isoformat()
           },
           {
               'id': '3',
               'title': 'Organic Chemistry',
               'description': 'Master the fundamentals of organic compounds and reactions',
               'topics': 'Alkenes,Aromatics,Reactions',
               'timestamp': datetime.now().isoformat()
           },
           {
               'id': '4',
               'title': 'Molecular Biology',
               'description': 'Deep dive into cellular processes and genetic mechanisms',
               'topics': 'DNA,Proteins,Cell Cycle',
               'timestamp': datetime.now().isoformat()
           }
       ]

def save_quizzes(quizzes):
   with open(QUIZZES_FILE, 'w') as f:
       json.dump(quizzes, f, indent=2)

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
       'password': generate_password_hash(signup_data['password'], method='sha256'),
       'strand': signup_data['strand'],
       'created_at': datetime.now().isoformat()
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
   if email not in users or not check_password_hash(users[email]['password'], password):
       flash('Invalid email or password', 'error')
       return redirect(url_for('index'))

   session['user_email'] = email
   session['username'] = users[email]['username']
   session['strand'] = users[email]['strand']
   
   return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
   if 'user_email' not in session:
       return redirect(url_for('index'))

   stories = load_stories()
   quizzes = load_quizzes()
   return render_template('dashboard.html',
                        username=session['username'],
                        strand=session['strand'],
                        stories=stories,
                        quizzes=quizzes)

@app.route('/create_post', methods=['POST'])
def create_post():
   if 'user_email' not in session:
       return redirect(url_for('index'))

   content = request.form.get('content')
   if not content:
       flash('Post content is required', 'error')
       return redirect(url_for('dashboard'))

   stories = load_stories()
   stories.append({
       'id': str(random.randint(1000, 9999)),
       'author': session['username'],
       'strand': session['strand'],
       'content': content,
       'timestamp': datetime.now().isoformat(),
       'likes': 0,
       'comments': []
   })
   save_stories(stories)

   return redirect(url_for('dashboard'))

@app.route('/like_post/<post_id>', methods=['POST'])
def like_post(post_id):
   if 'user_email' not in session:
       return redirect(url_for('index'))

   stories = load_stories()
   for story in stories:
       if story['id'] == post_id:
           story['likes'] += 1
           break
   save_stories(stories)

   return redirect(url_for('dashboard'))

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

   quiz_title = request.form.get('quiz_title')
   quiz_description = request.form.get('quiz_description')
   quiz_topics = request.form.get('quiz_topics')

   quizzes = load_quizzes()
   quizzes.append({
       'id': str(random.randint(1000, 9999)),
       'title': quiz_title,
       'description': quiz_description,
       'topics': quiz_topics,
       'timestamp': datetime.now().isoformat()
   })
   save_quizzes(quizzes)

   flash('Quiz posted successfully', 'success')
   return redirect(url_for('admin_dashboard'))

@app.route('/nimda/delete_quiz/<quiz_id>', methods=['POST'])
def admin_delete_quiz(quiz_id):
   if 'admin_logged_in' not in session:
       return redirect(url_for('admin_login'))

   quizzes = load_quizzes()
   quizzes = [quiz for quiz in quizzes if quiz['id'] != quiz_id]
   save_quizzes(quizzes)

   return '', 204

init_files()

if __name__ == '__main__':
   port = int(os.environ.get('PORT', 5000))
   app.run(host='0.0.0.0', port=port)