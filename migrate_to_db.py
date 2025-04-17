import os
import json
import pymysql
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'quiz_app')

# File paths
USERS_FILE = 'users.txt'
QUIZZES_FILE = 'quizzes.txt'

def get_db_connection():
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn

def migrate_users():
    try:
        # Load users from file
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        
        if not users:
            print("No users to migrate")
            return
        
        # Connect to database
        conn = get_db_connection()
        
        # Migrate each user
        count = 0
        try:
            with conn.cursor() as cursor:
                for email, user_data in users.items():
                    # Check if user already exists
                    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                    if cursor.fetchone():
                        print(f"User with email {email} already exists. Skipping.")
                        continue
                    
                    # Insert user
                    created_at = datetime.fromisoformat(user_data.get('created_at', datetime.now().isoformat()))
                    role = user_data.get('role', 'student')
                    
                    cursor.execute(
                        "INSERT INTO users (email, username, fullname, lrn, password, strand, role, created_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (
                            email,
                            user_data.get('username', ''),
                            user_data.get('fullname', ''),
                            user_data.get('lrn', ''),
                            user_data.get('password', ''),
                            user_data.get('strand', ''),
                            role,
                            created_at
                        )
                    )
                    count += 1
            
            conn.commit()
            print(f"Successfully migrated {count} users")
            
        except Exception as e:
            conn.rollback()
            print(f"Error migrating users: {e}")
        finally:
            conn.close()
    except Exception as e:
        print(f"Error reading users file: {e}")

def migrate_quizzes():
    try:
        # Load quizzes from file
        with open(QUIZZES_FILE, 'r') as f:
            quizzes = json.load(f)
        
        if not quizzes:
            print("No quizzes to migrate")
            return
        
        # Connect to database
        conn = get_db_connection()
        
        # Migrate each quiz
        count = 0
        question_count = 0
        try:
            with conn.cursor() as cursor:
                for quiz in quizzes:
                    # Insert quiz
                    created_at = datetime.fromisoformat(quiz.get('created_at', datetime.now().isoformat()))
                    
                    cursor.execute(
                        "INSERT INTO quizzes (title, description, category, strand, created_by, created_at, time_limit, passing_score) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (
                            quiz.get('title', ''),
                            quiz.get('description', ''),
                            quiz.get('category', ''),
                            quiz.get('strand', ''),
                            quiz.get('created_by', ''),
                            created_at,
                            quiz.get('time_limit', 0),
                            quiz.get('passing_score', 60)
                        )
                    )
                    
                    quiz_id = cursor.lastrowid
                    count += 1
                    
                    # Insert questions
                    questions = quiz.get('questions', [])
                    for question in questions:
                        # Convert options to JSON
                        options = json.dumps(question.get('options', [])) if question.get('options') else None
                        
                        cursor.execute(
                            "INSERT INTO quiz_questions (quiz_id, question, question_type, options, correct_answer, points) "
                            "VALUES (%s, %s, %s, %s, %s, %s)",
                            (
                                quiz_id,
                                question.get('text', ''),
                                question.get('type', 'multiple_choice'),
                                options,
                                question.get('answer', ''),
                                question.get('points', 1)
                            )
                        )
                        question_count += 1
            
            conn.commit()
            print(f"Successfully migrated {count} quizzes with {question_count} questions")
            
        except Exception as e:
            conn.rollback()
            print(f"Error migrating quizzes: {e}")
        finally:
            conn.close()
    except Exception as e:
        print(f"Error reading quizzes file: {e}")

if __name__ == "__main__":
    print("Starting migration...")
    migrate_users()
    migrate_quizzes()
    print("Migration completed!") 