from datetime import datetime
import random
import string
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='student')
    
    # Relations
    classes_taught = db.relationship('Class', back_populates='teacher')
    enrollments = db.relationship('ClassEnrollment', back_populates='enrolled_student')
    classes_enrolled = db.relationship('Class', 
                                     secondary='class_enrollments',
                                     back_populates='students',
                                     overlaps="enrollments")
    exercise_submissions = db.relationship('ExerciseSubmission', back_populates='submitting_student')
    exercises_created = db.relationship('Exercise', backref='creator', foreign_keys='Exercise.created_by')

    def __init__(self, username, email, password=None, role='student'):
        self.username = username
        self.email = email
        self.role = role
        if password:
            self.set_password(password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_teacher(self):
        return self.role == 'teacher'
    
    def get_teacher_stats(self):
        if not self.is_teacher:
            return None
            
        # Nombre total de classes
        total_classes = len(self.classes_taught)
        
        # Nombre total d'élèves (utiliser un set pour éviter les doublons)
        students = set()
        for class_ in self.classes_taught:
            students.update(student.id for student in class_.students)
        total_students = len(students)
        
        # Nombre total d'exercices (inclure tous les exercices dans les cours des classes)
        total_exercises = 0
        for class_ in self.classes_taught:
            for course in class_.courses:
                total_exercises += len(course.exercises)
        
        return {
            'total_classes': total_classes,
            'total_students': total_students,
            'total_exercises': total_exercises
        }

class Class(db.Model):
    __tablename__ = 'class'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    invite_code = db.Column(db.String(6), nullable=True, server_default=None)

    # Relations
    teacher = db.relationship('User', back_populates='classes_taught')
    enrollments = db.relationship('ClassEnrollment', back_populates='enrolled_class')
    students = db.relationship('User', 
                             secondary='class_enrollments',
                             back_populates='classes_enrolled',
                             overlaps="enrollments")
    courses = db.relationship('Course', backref='class_', lazy=True)
    exercises = db.relationship('Exercise',
                              secondary='class_exercises',
                              backref=db.backref('classes', lazy='dynamic'),
                              lazy='dynamic')

    def __init__(self, name, description, teacher_id):
        self.name = name
        self.description = description
        self.teacher_id = teacher_id
        self.invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    def generate_invite_code(self):
        self.invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return self.invite_code

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text)  # Contenu riche du cours
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    exercises = db.relationship('Exercise', backref='course', lazy=True)
    files = db.relationship('CourseFile', backref='course', cascade='all, delete-orphan')

class Exercise(db.Model):
    __tablename__ = 'exercise'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    exercise_type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text)
    solution = db.Column(db.Text)
    difficulty = db.Column(db.String(20))
    points = db.Column(db.Integer)
    subject = db.Column(db.String(100))
    level = db.Column(db.String(50))  # Ajout du champ level
    image_path = db.Column(db.String(255))
    is_in_library = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=True)  
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relations
    submissions = db.relationship('ExerciseSubmission', back_populates='exercise', overlaps="exercise")
    questions = db.relationship('Question', backref='exercise', lazy=True, cascade='all, delete-orphan')
    text_holes = db.relationship('TextHole', backref='exercise', lazy=True, cascade='all, delete-orphan')
    pair_matches = db.relationship('PairMatch', backref='exercise', lazy=True, cascade='all, delete-orphan')
    
    # Alias pour la compatibilité
    @property
    def teacher_id(self):
        return self.created_by

class PairMatch(db.Model):
    __tablename__ = 'pair_matches'
    id = db.Column(db.Integer, primary_key=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    left_type = db.Column(db.String(10), nullable=False)  # 'text' ou 'image'
    right_type = db.Column(db.String(10), nullable=False)  # 'text' ou 'image'
    left_content = db.Column(db.Text, nullable=False)  # texte ou chemin de l'image
    right_content = db.Column(db.Text, nullable=False)  # texte ou chemin de l'image
    position = db.Column(db.Integer)  # pour l'ordre des paires

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(255))  # Chemin de l'image
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    
    # Relations
    choices = db.relationship('Choice', backref='question', lazy=True, cascade='all, delete-orphan')

class Choice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)

class TextHole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text_before = db.Column(db.Text)
    correct_answer = db.Column(db.String(100), nullable=False)
    text_after = db.Column(db.Text)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)

class ExerciseSubmission(db.Model):
    __tablename__ = 'exercise_submission'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    answers = db.Column(db.JSON)
    score = db.Column(db.Float)
    feedback = db.Column(db.Text)  # Ajout du champ feedback
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    submitting_student = db.relationship('User', back_populates='exercise_submissions')
    exercise = db.relationship('Exercise', back_populates='submissions', overlaps="submitted_exercise")

class CourseFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

class ClassEnrollment(db.Model):
    __tablename__ = 'class_enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    enrolled_class = db.relationship('Class', back_populates='enrollments', overlaps="classes_enrolled,students")
    enrolled_student = db.relationship('User', back_populates='enrollments', overlaps="classes_enrolled,students")

class ClassExercise(db.Model):
    __tablename__ = 'class_exercises'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
