"""
AI Exam Checker - Main Application
Industry-level Flask application for automated answer evaluation using BERT and OCR
"""

import os
import sqlite3
import bcrypt
from functools import wraps
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename

# Import AI models
from model.bert_model import evaluate_answer as bert_evaluate
from model.ocr import extract_text_from_image

# Configuration
app = Flask(__name__)
app.secret_key = 'ai_exam_checker_secret_key_2024'

# Database configuration
DATABASE = 'database/database.db'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('database', exist_ok=True)


# ==================== Database Functions ====================

def init_database():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_username TEXT NOT NULL,
            exam_name TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            student_answer TEXT NOT NULL,
            marks REAL NOT NULL,
            similarity REAL NOT NULL,
            evaluated_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ==================== Helper Functions ====================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def hash_password(password):
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())


def check_password(password, hashed):
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)


def login_required(f):
    """Decorator for routes requiring login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Decorator for routes requiring specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please login to access this page.', 'danger')
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ==================== Routes ====================

@app.route('/')
def index():
    """Redirect to login page"""
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password(password, user['password']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            flash(f'Welcome back, {user["username"]}!', 'success')
            
            # Redirect based on role
            if user['role'] == 'Admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'Teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')
        
        # Validation
        if not username or not password or not role:
            flash('All fields are required.', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')
        
        # Check if username exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            flash('Username already exists.', 'danger')
            conn.close()
            return render_template('register.html')
        
        # Create user
        try:
            hashed_password = hash_password(password)
            cursor.execute(
                'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                (username, hashed_password, role)
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error during registration: {str(e)}', 'danger')
        finally:
            conn.close()
    
    return render_template('register.html')


@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/admin_dashboard')
@login_required
@role_required('Admin')
def admin_dashboard():
    """Admin dashboard"""
    conn = get_db_connection()
    
    # Get statistics
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total FROM users')
    total_users = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(*) as total FROM results')
    total_exams = cursor.fetchone()['total']
    
    cursor.execute('SELECT AVG(marks) as avg FROM results')
    avg_marks = cursor.fetchone()['avg'] or 0
    
    # Get all users
    cursor.execute('SELECT id, username, role, created_at FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    
    # Get recent results
    cursor.execute('''
        SELECT r.*, u.username as evaluator_name 
        FROM results r 
        LEFT JOIN users u ON r.evaluated_by = u.username
        ORDER BY r.created_at DESC LIMIT 10
    ''')
    recent_results = cursor.fetchall()
    
    conn.close()
    
    return render_template(
        'admin_dashboard.html',
        total_users=total_users,
        total_exams=total_exams,
        avg_marks=round(avg_marks, 2),
        users=users,
        recent_results=recent_results
    )


@app.route('/teacher_dashboard', methods=['GET', 'POST'])
@login_required
@role_required('Teacher')
def teacher_dashboard():
    """Teacher dashboard"""
    if request.method == 'POST':
        exam_name = request.form.get('exam_name')
        correct_answer = request.form.get('correct_answer')
        student_answer = request.form.get('student_answer')
        student_username = request.form.get('student_username')
        use_ocr = request.form.get('use_ocr')
        
        # Handle file upload for OCR
        if 'answer_image' in request.files:
            file = request.files['answer_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Extract text using OCR
                try:
                    student_answer = extract_text_from_image(filepath)
                    flash('Text extracted from image using OCR.', 'info')
                except Exception as e:
                    flash(f'OCR Error: {str(e)}', 'danger')
                    return render_template('teacher_dashboard.html')
        
        # Validate inputs
        if not exam_name or not correct_answer or not student_username:
            flash('Exam name, student username, and correct answer are required.', 'danger')
            return render_template('teacher_dashboard.html')
        
        # If no student answer provided and no image, show error
        if not student_answer:
            flash('Please provide a student answer or upload an answer sheet image.', 'danger')
            return render_template('teacher_dashboard.html')
        
        # Evaluate using BERT
        try:
            result = bert_evaluate(correct_answer, student_answer)
            
            # Save result to database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO results 
                (student_username, exam_name, correct_answer, student_answer, marks, similarity, evaluated_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                student_username,
                exam_name,
                correct_answer,
                student_answer,
                result['marks'],
                result['similarity_score'],
                session['username']
            ))
            conn.commit()
            conn.close()
            
            flash(f'Evaluation complete! Similarity: {result["similarity_score"]}%, Marks: {result["marks"]}/{result["max_marks"]}', 'success')
            
            return render_template(
                'teacher_dashboard.html',
                result=result,
                exam_name=exam_name,
                student_username=student_username
            )
            
        except Exception as e:
            flash(f'Error during evaluation: {str(e)}', 'danger')
    
    return render_template('teacher_dashboard.html')


@app.route('/student_dashboard')
@login_required
@role_required('Student')
def student_dashboard():
    """Student dashboard"""
    username = session.get('username')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get student's results
    cursor.execute('''
        SELECT * FROM results 
        WHERE student_username = ?
        ORDER BY created_at DESC
    ''', (username,))
    results = cursor.fetchall()
    
    # Calculate statistics
    cursor.execute('''
        SELECT AVG(marks) as avg_marks, MAX(marks) as max_marks, MIN(marks) as min_marks
        FROM results WHERE student_username = ?
    ''', (username,))
    stats = cursor.fetchone()
    
    conn.close()
    
    avg_marks = round(stats['avg_marks'], 2) if stats['avg_marks'] else 0
    max_marks = stats['max_marks'] if stats['max_marks'] else 0
    min_marks = stats['min_marks'] if stats['min_marks'] else 0
    
    # Prepare chart data
    chart_labels = [r['exam_name'] for r in results]
    chart_marks = [r['marks'] for r in results]
    
    return render_template(
        'student_dashboard.html',
        results=results,
        avg_marks=avg_marks,
        max_marks=max_marks,
        min_marks=min_marks,
        total_exams=len(results),
        chart_labels=chart_labels,
        chart_marks=chart_marks
    )


@app.route('/analytics')
@login_required
def analytics():
    """Analytics page with charts"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all results for analytics
    cursor.execute('''
        SELECT student_username, exam_name, marks, similarity, created_at
        FROM results
        ORDER BY created_at DESC
    ''')
    all_results = cursor.fetchall()
    
    # Get statistics
    cursor.execute('SELECT COUNT(*) as total FROM results')
    total_exams = cursor.fetchone()['total']
    
    cursor.execute('SELECT AVG(marks) as avg FROM results')
    avg_marks = cursor.fetchone()['avg'] or 0
    
    cursor.execute('SELECT AVG(similarity) as avg FROM results')
    avg_similarity = cursor.fetchone()['avg'] or 0
    
    # Get marks distribution
    cursor.execute('''
        SELECT 
            CASE 
                WHEN marks >= 90 THEN '90-100'
                WHEN marks >= 80 THEN '80-89'
                WHEN marks >= 70 THEN '70-79'
                WHEN marks >= 60 THEN '60-69'
                WHEN marks >= 50 THEN '50-59'
                ELSE '0-49'
            END as range,
            COUNT(*) as count
        FROM results
        GROUP BY range
    ''')
    marks_distribution = cursor.fetchall()
    
    # Get student performance
    cursor.execute('''
        SELECT student_username, AVG(marks) as avg_marks, COUNT(*) as exam_count
        FROM results
        GROUP BY student_username
        ORDER BY avg_marks DESC
    ''')
    student_performance = cursor.fetchall()
    
    conn.close()
    
    # Prepare chart data
    distribution_labels = [r['range'] for r in marks_distribution]
    distribution_data = [r['count'] for r in marks_distribution]
    
    performance_labels = [r['student_username'] for r in student_performance]
    performance_data = [round(r['avg_marks'], 2) for r in student_performance]
    
    return render_template(
        'analytics.html',
        total_exams=total_exams,
        avg_marks=round(avg_marks, 2),
        avg_similarity=round(avg_similarity, 2),
        distribution_labels=distribution_labels,
        distribution_data=distribution_data,
        performance_labels=performance_labels,
        performance_data=performance_data,
        all_results=all_results
    )


@app.route('/evaluate', methods=['POST'])
@login_required
@role_required('Teacher')
def evaluate():
    """API endpoint for evaluating answers"""
    data = request.get_json()
    
    correct_answer = data.get('correct_answer')
    student_answer = data.get('student_answer')
    
    if not correct_answer or not student_answer:
        return jsonify({'error': 'Both correct answer and student answer are required'}), 400
    
    try:
        result = bert_evaluate(correct_answer, student_answer)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/upload', methods=['POST'])
@login_required
@role_required('Teacher')
def upload():
    """API endpoint for OCR upload"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            text = extract_text_from_image(filepath)
            return jsonify({'text': text, 'filename': filename})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400


# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(e):
    """404 error handler"""
    return render_template('login.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    """500 error handler"""
    return render_template('login.html', error='Internal server error'), 500


# ==================== Main ====================

if __name__ == '__main__':
    # Initialize database
    init_database()
    
    # Run app
    print("\n" + "="*60)
    print("AI Exam Checker Application")
    print("="*60)
    print("Server starting at: http://127.0.0.1:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
