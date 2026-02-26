from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'faculty', 'student'
    full_name = db.Column(db.String(100), nullable=False)

    # Secondary relationship for profiles
    student_profile = db.relationship('StudentProfile', backref='user', uselist=False)
    faculty_profile = db.relationship('FacultyProfile', backref='user', uselist=False)
    leaves = db.relationship('LeaveRequest', backref='student', lazy=True)

class StudentProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    roll_number = db.Column(db.String(20), unique=True, nullable=False)
    batch = db.Column(db.String(20)) # e.g., '2022-2026'
    department = db.Column(db.String(50))

class FacultyProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    department = db.Column(db.String(50))

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    faculty = db.relationship('User', backref='subjects')

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    status = db.Column(db.String(10), nullable=False) # 'Present', 'Absent'
    subject = db.relationship('Subject', backref='attendance_records')

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    request_type = db.Column(db.String(20), default='Leave') # 'Leave' or 'OD'
    status = db.Column(db.String(20), default='Pending') # 'Pending', 'Approved', 'Rejected'
    applied_on = db.Column(db.DateTime, default=datetime.utcnow)
