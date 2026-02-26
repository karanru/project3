from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, StudentProfile, FacultyProfile, Subject, Attendance, LeaveRequest
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        users_count = User.query.count()
        students_count = User.query.filter_by(role='student').count()
        faculty_count = User.query.filter_by(role='faculty').count()
        return render_template('admin_dashboard.html', students=students_count, faculty=faculty_count)
    elif current_user.role == 'faculty':
        subjects = Subject.query.filter_by(faculty_id=current_user.id).all()
        leaves = LeaveRequest.query.filter_by(status='Pending').all()
        return render_template('faculty_dashboard.html', subjects=subjects, leaves=leaves)
    else:
        # Calculate attendance percentage
        total = Attendance.query.filter_by(student_id=current_user.id).count()
        present = Attendance.query.filter_by(student_id=current_user.id, status='Present').count()
        percent = (present / total * 100) if total > 0 else 0
        history = Attendance.query.filter_by(student_id=current_user.id).order_by(Attendance.date.desc()).all()
        student_leaves = LeaveRequest.query.filter_by(student_id=current_user.id).order_by(LeaveRequest.applied_on.desc()).all()
        return render_template('student_dashboard.html', percentage=percent, history=history, leaves=student_leaves)

@app.route('/mark_attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    if current_user.role != 'faculty':
        return redirect(url_for('dashboard'))
    
    students = User.query.filter_by(role='student').all()
    subjects = Subject.query.filter_by(faculty_id=current_user.id).all()
    
    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        
        for student in students:
            status = request.form.get(f'status_{student.id}')
            # Check if already marked
            existing = Attendance.query.filter_by(student_id=student.id, subject_id=subject_id, date=date).first()
            if existing:
                existing.status = status
            else:
                att = Attendance(student_id=student.id, subject_id=subject_id, date=date, status=status)
                db.session.add(att)
        
        db.session.commit()
        flash('Attendance marked successfully')
        return redirect(url_for('dashboard'))
        
    return render_template('mark_attendance.html', students=students, subjects=subjects)

@app.route('/apply_leave', methods=['POST'])
@login_required
def apply_leave():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))
    
    start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
    end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
    reason = request.form.get('reason')
    request_type = request.form.get('request_type', 'Leave')
    
    leave = LeaveRequest(student_id=current_user.id, start_date=start_date, end_date=end_date, reason=reason, request_type=request_type)
    db.session.add(leave)
    db.session.commit()
    flash('Leave application submitted')
    return redirect(url_for('dashboard'))

@app.route('/manage_leaves', methods=['GET', 'POST'])
@login_required
def manage_leaves():
    if current_user.role != 'faculty':
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        leave_id = request.form.get('leave_id')
        action = request.form.get('action') # 'Approved' or 'Rejected'
        leave = LeaveRequest.query.get(leave_id)
        if leave:
            leave.status = action
            db.session.commit()
            flash(f'Leave {action}')
            
    leaves = LeaveRequest.query.filter_by(status='Pending').all()
    return render_template('manage_leaves.html', leaves=leaves)

@app.route('/manage_users', methods=['GET'])
@login_required
def manage_users():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    users = User.query.filter(User.role != 'admin').all()
    return render_template('manage_users.html', users=users)

@app.route('/manage_subjects', methods=['GET'])
@login_required
def manage_subjects():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    subjects = Subject.query.all()
    faculty_list = User.query.filter_by(role='faculty').all()
    return render_template('manage_subjects.html', subjects=subjects, faculty_list=faculty_list)

@app.route('/add_subject', methods=['POST'])
@login_required
def add_subject():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    name = request.form.get('name')
    code = request.form.get('code')
    faculty_id = request.form.get('faculty_id')
    
    if Subject.query.filter_by(code=code).first():
        flash('Subject code already exists')
        return redirect(url_for('manage_subjects'))
    
    new_sub = Subject(name=name, code=code, faculty_id=faculty_id)
    db.session.add(new_sub)
    db.session.commit()
    flash('Subject added successfully')
    return redirect(url_for('manage_subjects'))

@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    username = request.form.get('username')
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists')
        return redirect(url_for('manage_users'))
    
    new_user = User(
        username=username,
        full_name=full_name,
        email=email,
        password=generate_password_hash(password),
        role=role
    )
    db.session.add(new_user)
    db.session.commit()
    
    # Create profile
    if role == 'student':
        prof = StudentProfile(user_id=new_user.id, roll_number=f"S{new_user.id:03}", batch="2024", department="Computer Science")
        db.session.add(prof)
    else:
        prof = FacultyProfile(user_id=new_user.id, employee_id=f"F{new_user.id:03}", department="Computer Science")
        db.session.add(prof)
        
    db.session.commit()
    flash('User added successfully')
    return redirect(url_for('manage_users'))

@app.route('/reports')
@login_required
def reports():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    students = User.query.filter_by(role='student').all()
    report_data = []
    total_present = 0
    total_absent = 0
    
    for s in students:
        present = Attendance.query.filter_by(student_id=s.id, status='Present').count()
        absent = Attendance.query.filter_by(student_id=s.id, status='Absent').count()
        total = present + absent
        pct = (present / total * 100) if total > 0 else 0
        
        report_data.append({
            'full_name': s.full_name,
            'roll_number': s.student_profile.roll_number if s.student_profile else 'N/A',
            'present': present,
            'absent': absent,
            'percentage': pct
        })
        total_present += present
        total_absent += absent
        
    overall_total = total_present + total_absent
    overall_pct = (total_present / overall_total * 100) if overall_total > 0 else 0
    
    return render_template('reports.html', report_data=report_data, overall_pct=overall_pct)

# Database Initialization
with app.app_context():
    db.create_all()
    # Create default admin if not exists
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            password=generate_password_hash('admin123'),
            email='admin@college.edu',
            role='admin',
            full_name='System Admin'
        )
        db.session.add(admin_user)
        db.session.commit()
    
    # Seed sample faculty and student if empty
    if User.query.count() <= 1:
        f = User(username='faculty', password=generate_password_hash('pass123'), email='f@college.edu', role='faculty', full_name='Dr. Smith')
        db.session.add(f)
        db.session.flush()
        fp = FacultyProfile(user_id=f.id, employee_id='EMP001', department='CS')
        db.session.add(fp)
        
        s = User(username='student', password=generate_password_hash('pass123'), email='s@college.edu', role='student', full_name='John Doe')
        db.session.add(s)
        db.session.flush()
        sp = StudentProfile(user_id=s.id, roll_number='CS101', batch='2024', department='CS')
        db.session.add(sp)
        
        sub = Subject(name='Python Programming', code='CS50', faculty_id=f.id)
        db.session.add(sub)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
