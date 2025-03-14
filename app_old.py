import os
import logging
from datetime import datetime, timezone
from functools import wraps
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, url_for, flash, redirect, request, jsonify, send_from_directory, abort, session, send_file, current_app
from flask_login import login_user, current_user, logout_user, login_required, LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload
import json
from datetime import timedelta
from urllib.parse import urlparse

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

logger.info('Application démarrée')

import sys
from extensions import db, migrate, bcrypt, login_manager, csrf

# Configuration des dossiers
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

# Import des formulaires
from forms import (LoginForm, RegistrationForm, ClassForm, CourseForm, 
                  ExerciseForm, GradeForm, TextHoleForm, QuestionForm, ChoiceForm,
                  PairMatchForm, JoinClassForm)

# Configuration de l'application
app = Flask(__name__)
app.config.from_object('config')

# Configuration des dossiers statiques
app.static_folder = 'static'
app.static_url_path = '/static'

# Initialisation des extensions
db.init_app(app)
migrate.init_app(app, db)
bcrypt.init_app(app)
csrf.init_app(app)
login_manager.init_app(app)

# Configuration de Flask-Login
login_manager.login_view = 'login'
login_manager.session_protection = "strong"

# Import des modèles et des utilitaires
from models import User, Class, Course, Exercise, ExerciseSubmission, CourseFile, Question, Choice, TextHole, ClassEnrollment, ClassExercise, PairMatch
from logs import logger, log_database_error, log_form_data, log_model_creation, log_request_info

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Filtre Jinja pour convertir le JSON en objet Python
@app.template_filter('from_json')
def from_json(value):
    return json.loads(value) if value else []

# Créer le dossier uploads s'il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Décorateur pour restreindre l'accès aux enseignants
def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_teacher:
            flash('Accès non autorisé. Vous devez être un enseignant.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/exercise_stats')
@login_required
@teacher_required
def exercise_stats():
    try:
        # Récupérer les exercices de l'enseignant
        teacher_exercises = Exercise.query\
            .join(Course)\
            .join(Class)\
            .filter(
                Class.teacher_id == current_user.id,
                Exercise.points > 0
            )\
            .all()
        
        exercise_stats = []
        total_submissions = 0
        total_score = 0
        valid_submissions = 0

        for exercise in teacher_exercises:
            # Récupérer les soumissions avec leurs étudiants
            submissions = ExerciseSubmission.query\
                .join(User)\
                .filter(
                    ExerciseSubmission.exercise_id == exercise.id,
                    ExerciseSubmission.score.isnot(None)
                )\
                .all()
            
            exercise_data = {
                'class_name': exercise.course.class_.name,
                'exercise_name': exercise.title,
                'exercise_id': exercise.id,
                'submission_count': len(submissions),
                'average_score': 0,
                'submissions': []
            }
            
            exercise_total = 0
            exercise_valid = 0
            
            for submission in submissions:
                if submission.score is not None and submission.score >= 0:
                    try:
                        score = (submission.score / exercise.points) * 100
                        score = min(round(score, 1), 100)
                        exercise_total += score
                        exercise_valid += 1
                        exercise_data['submissions'].append({
                            'student_name': f"{submission.submitting_student.first_name} {submission.submitting_student.last_name}",
                            'score': score
                        })
                    except:
                        continue
            
            if exercise_valid > 0:
                exercise_data['average_score'] = round(exercise_total / exercise_valid, 1)
                total_score += exercise_total
                valid_submissions += exercise_valid
            
            total_submissions += len(submissions)
            exercise_data['submissions'].sort(key=lambda x: x['score'], reverse=True)
            exercise_stats.append(exercise_data)
        
        # Trier les exercices par moyenne
        exercise_stats.sort(key=lambda x: x['average_score'], reverse=True)
        
        return render_template('exercise_stats.html',
                             exercise_details=exercise_stats,
                             total_submissions=total_submissions,
                             total_exercises=len(teacher_exercises),
                             total_score_percentage=round(total_score / valid_submissions, 1) if valid_submissions > 0 else 0)
    
    except Exception as e:
        logger.error(f"Erreur lors de l'affichage des statistiques: {str(e)}")
        flash("Une erreur s'est produite lors du chargement des statistiques.", "danger")
        return redirect(url_for('teacher_dashboard'))

@app.route('/exercise/<int:exercise_id>/stats')
@login_required
@teacher_required
def exercise_specific_stats(exercise_id):
    try:
        # Récupérer l'exercice avec ses relations
        exercise = Exercise.query\
            .join(Course)\
            .join(Class)\
            .filter(Exercise.id == exercise_id)\
            .first_or_404()
        
        # Vérifier l'accès
        if exercise.course.class_.teacher_id != current_user.id:
            flash("Vous n'avez pas accès à ces statistiques.", "danger")
            return redirect(url_for('teacher_dashboard'))
        
        # Vérifier si l'exercice a des points
        if not exercise.points or exercise.points <= 0:
            flash("Cet exercice n'a pas de points attribués.", "warning")
            return redirect(url_for('exercise_stats'))
        
        # Récupérer les soumissions avec leurs étudiants
        submissions = ExerciseSubmission.query\
            .join(User)\
            .filter(
                ExerciseSubmission.exercise_id == exercise_id,
                ExerciseSubmission.score.isnot(None)
            )\
            .all()
        
        # Initialiser les statistiques
        stats = {
            'title': exercise.title,
            'submission_count': len(submissions),
            'average_score': 0,
            'max_score': 0,
            'min_score': 100,
            'submissions': [],
            'score_distribution': {
                (0, 25): 0,
                (25, 50): 0,
                (50, 75): 0,
                (75, 100): 0
            }
        }
        
        total_score = 0
        valid_count = 0
        
        for submission in submissions:
            if submission.score is not None and submission.score >= 0:
                try:
                    # Calculer le score en pourcentage
                    score = (submission.score / exercise.points) * 100
                    score = min(round(score, 1), 100)
                    
                    total_score += score
                    valid_count += 1
                    
                    # Mettre à jour les scores min/max
                    stats['max_score'] = max(stats['max_score'], score)
                    stats['min_score'] = min(stats['min_score'], score)
                    
                    # Ajouter les détails de la soumission
                    stats['submissions'].append({
                        'student_name': f"{submission.submitting_student.first_name} {submission.submitting_student.last_name}",
                        'submitted_at': submission.submitted_at,
                        'score_percentage': score
                    })
                    
                    # Mettre à jour la distribution des scores
                    for start, end in [(0, 25), (25, 50), (50, 75), (75, 100)]:
                        if start <= score <= end:
                            stats['score_distribution'][(start, end)] += 1
                            break
                except Exception as e:
                    logger.warning(f"Erreur de calcul pour la soumission {submission.id}: {str(e)}")
                    continue
        
        # Calculer la moyenne si nous avons des soumissions valides
        if valid_count > 0:
            stats['average_score'] = round(total_score / valid_count, 1)
        if valid_count == 0:
            stats['min_score'] = 0
        
        # Trier les soumissions par score
        stats['submissions'].sort(key=lambda x: x['score_percentage'], reverse=True)
        
        return render_template('exercise_specific_stats.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'affichage des statistiques détaillées: {str(e)}")
        flash("Une erreur s'est produite lors du chargement des statistiques détaillées.", "danger")
        return redirect(url_for('exercise_stats'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.user_type.data
        )
        user.set_password(form.password.data)
        try:
            db.session.add(user)
            db.session.commit()
            flash('Votre compte a été créé avec succès! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création du compte: {str(e)}")
            flash('Une erreur est survenue lors de la création du compte. Veuillez réessayer.', 'danger')
    return render_template('register.html', title='Inscription', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Connexion réussie!', 'success')
            if next_page:
                return redirect(next_page)
            elif user.is_teacher:
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Email ou mot de passe incorrect.', 'danger')
    return render_template('login.html', title='Connexion', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/teacher_dashboard')
@login_required
@teacher_required
def teacher_dashboard():
    return render_template('teacher_dashboard.html')

@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if current_user.is_teacher:
        return redirect(url_for('teacher_dashboard'))
    return render_template('student_dashboard.html')

@app.route('/create_class', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_class():
    form = ClassForm()
    if form.validate_on_submit():
        new_class = Class(
            name=form.name.data,
            description=form.description.data,
            teacher_id=current_user.id
        )
        try:
            db.session.add(new_class)
            db.session.commit()
            flash(f'La classe {form.name.data} a été créée avec succès!', 'success')
            return redirect(url_for('teacher_dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création de la classe: {str(e)}")
            flash('Une erreur est survenue lors de la création de la classe.', 'danger')
    return render_template('create_class.html', title='Créer une classe', form=form)

@app.route('/class/<int:class_id>')
@login_required
def view_class(class_id):
    class_ = Class.query.get_or_404(class_id)
    if not current_user.is_teacher and current_user not in class_.students:
        flash("Vous n'avez pas accès à cette classe.", "danger")
        return redirect(url_for('student_dashboard'))
    return render_template('view_class.html', class_=class_)

@app.route('/class/<int:class_id>/create_course', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_course(class_id):
    class_ = Class.query.get_or_404(class_id)
    if class_.teacher_id != current_user.id:
        flash("Vous n'avez pas l'autorisation de créer un cours dans cette classe.", "danger")
        return redirect(url_for('teacher_dashboard'))
    
    form = CourseForm()
    if form.validate_on_submit():
        course = Course(
            title=form.title.data,
            description=form.description.data,
            content=form.content.data,
            class_id=class_id
        )
        try:
            db.session.add(course)
            db.session.commit()
            
            # Gestion des fichiers
            if form.files.data:
                for file in form.files.data:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(UPLOAD_FOLDER, filename)
                        file.save(file_path)
                        course_file = CourseFile(
                            filename=filename,
                            file_path=file_path,
                            course_id=course.id
                        )
                        db.session.add(course_file)
                db.session.commit()
            
            flash('Le cours a été créé avec succès!', 'success')
            return redirect(url_for('view_class', class_id=class_id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création du cours: {str(e)}")
            flash('Une erreur est survenue lors de la création du cours.', 'danger')
    
    return render_template('create_course.html', title='Créer un cours', form=form, class_=class_)

@app.route('/course/<int:course_id>/create_exercise', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_exercise(course_id):
    course = Course.query.get_or_404(course_id)
    if course.class_.teacher_id != current_user.id:
        flash("Vous n'avez pas l'autorisation de créer un exercice dans ce cours.", "danger")
        return redirect(url_for('teacher_dashboard'))
    
    form = ExerciseForm()
    form.course_id.choices = [(course.id, course.title)]
    
    if form.validate_on_submit():
        exercise = Exercise(
            title=form.title.data,
            description=form.description.data,
            exercise_type=form.exercise_type.data,
            difficulty=form.difficulty.data,
            points=form.points.data,
            subject=form.subject.data,
            level=form.level.data,
            course_id=course.id,
            created_by=current_user.id
        )
        
        try:
            # Gestion de l'image
            if form.image.data:
                filename = secure_filename(form.image.data.filename)
                image_path = os.path.join(UPLOAD_FOLDER, filename)
                form.image.data.save(image_path)
                exercise.image_path = filename
            
            db.session.add(exercise)
            db.session.commit()
            
            # Gestion des questions selon le type d'exercice
            if form.exercise_type.data == 'QCM':
                for question_form in form.questions.data:
                    if question_form.get('text'):
                        question = Question(
                            text=question_form['text'],
                            exercise_id=exercise.id
                        )
                        db.session.add(question)
                        db.session.flush()
                        
                        for choice_form in question_form.get('choices', []):
                            if choice_form.get('text'):
                                choice = Choice(
                                    text=choice_form['text'],
                                    is_correct=choice_form.get('is_correct', False),
                                    question_id=question.id
                                )
                                db.session.add(choice)
            
            elif form.exercise_type.data == 'text_holes':
                for hole_form in form.text_holes.data:
                    if hole_form.get('correct_answer'):
                        hole = TextHole(
                            text_before=hole_form.get('text_before', ''),
                            correct_answer=hole_form['correct_answer'],
                            text_after=hole_form.get('text_after', ''),
                            exercise_id=exercise.id
                        )
                        db.session.add(hole)
            
            elif form.exercise_type.data == 'PAIR_MATCH':
                for pair_form in form.pair_matches.data:
                    if pair_form.get('left_content') and pair_form.get('right_content'):
                        pair = PairMatch(
                            left_type=pair_form['left_type'],
                            right_type=pair_form['right_type'],
                            left_content=pair_form['left_content'],
                            right_content=pair_form['right_content'],
                            exercise_id=exercise.id
                        )
                        db.session.add(pair)
            
            db.session.commit()
            flash('L\'exercice a été créé avec succès!', 'success')
            return redirect(url_for('view_course', course_id=course.id))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création de l'exercice: {str(e)}")
            flash('Une erreur est survenue lors de la création de l\'exercice.', 'danger')
    
    return render_template('create_exercise.html', title='Créer un exercice', form=form, course=course)

@app.route('/course/<int:course_id>')
@login_required
def view_course(course_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_teacher and current_user not in course.class_.students:
        flash("Vous n'avez pas accès à ce cours.", "danger")
        return redirect(url_for('student_dashboard'))
    return render_template('view_course.html', course=course)

@app.route('/exercise/<int:exercise_id>')
@login_required
def view_exercise(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    if not current_user.is_teacher and current_user not in exercise.course.class_.students:
        flash("Vous n'avez pas accès à cet exercice.", "danger")
        return redirect(url_for('student_dashboard'))
    return render_template('exercise.html', exercise=exercise)

@app.route('/join_class', methods=['GET', 'POST'])
@login_required
def join_class():
    if current_user.is_teacher:
        flash("Les enseignants ne peuvent pas rejoindre de classe.", "warning")
        return redirect(url_for('teacher_dashboard'))
    
    form = JoinClassForm()
    if form.validate_on_submit():
        class_ = Class.query.filter_by(invite_code=form.invite_code.data).first()
        if class_:
            if current_user in class_.students:
                flash("Vous êtes déjà inscrit dans cette classe.", "info")
            else:
                enrollment = ClassEnrollment(student_id=current_user.id, class_id=class_.id)
                try:
                    db.session.add(enrollment)
                    db.session.commit()
                    flash(f"Vous avez rejoint la classe {class_.name} avec succès!", "success")
                    return redirect(url_for('view_class', class_id=class_.id))
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Erreur lors de l'inscription à la classe: {str(e)}")
                    flash("Une erreur est survenue lors de l'inscription à la classe.", "danger")
        else:
            flash("Code d'invitation invalide.", "danger")
    
    return render_template('join_class.html', title='Rejoindre une classe', form=form)

if __name__ == '__main__':
    app.run(debug=True)
