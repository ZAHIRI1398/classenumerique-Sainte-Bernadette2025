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
import random
import string

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
app.config['SECRET_KEY'] = 'votre_clé_secrète_ici'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['SESSION_COOKIE_SECURE'] = False  # Pour le développement local
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 heure en secondes
app.config['WTF_CSRF_SECRET_KEY'] = 'une_autre_clé_secrète_ici'

# Initialisation des extensions
db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)
login_manager.login_view = 'login'

# Configuration de Flask-Login
login_manager.session_protection = "strong"

# Import des modèles et des utilitaires
from models import User, Class, Course, Exercise, ExerciseSubmission, CourseFile, Question, Choice, TextHole, ClassEnrollment, ClassExercise, PairMatch
from logs import logger, log_database_error, log_form_data, log_model_creation, log_request_info

@login_manager.user_loader
def load_user(user_id):
    print(f"Loading user {user_id}")  # Debug print
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
        if not current_user.is_authenticated or current_user.role != 'teacher':
            flash('Accès non autorisé. Vous devez être un enseignant.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Routes de base
@app.route('/')
@app.route('/index')
def index():
    if current_user.is_authenticated:
        if current_user.is_teacher:
            return redirect(url_for('teacher_dashboard'))
        return redirect(url_for('student_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Route pour la connexion des utilisateurs."""
    if current_user.is_authenticated:
        if current_user.is_teacher:
            return redirect(url_for('teacher_dashboard'))
        elif 'current_class_id' in session:
            return redirect(url_for('student_dashboard'))
        else:
            classes_enrolled = current_user.classes_enrolled
            if len(classes_enrolled) == 1:
                session['current_class_id'] = classes_enrolled[0].id
                return redirect(url_for('student_dashboard'))
            elif len(classes_enrolled) > 1:
                return redirect(url_for('select_class'))
            else:
                flash('Vous n\'êtes inscrit à aucune classe.', 'warning')
                return redirect(url_for('join_class'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            session.permanent = True  # Utiliser la durée de session permanente
            
            # Si c'est un étudiant
            if not user.is_teacher:
                classes_enrolled = user.classes_enrolled
                if len(classes_enrolled) == 1:
                    session['current_class_id'] = classes_enrolled[0].id
                    return redirect(url_for('student_dashboard'))
                elif len(classes_enrolled) > 1:
                    return redirect(url_for('select_class'))
                else:
                    flash('Vous n\'êtes inscrit à aucune classe.', 'warning')
                    return redirect(url_for('join_class'))
            else:
                return redirect(url_for('teacher_dashboard'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'danger')
            
    return render_template('login.html', form=form)

@app.route('/select_class')
@login_required
def select_class():
    """Route pour sélectionner une classe si l'étudiant est inscrit dans plusieurs classes."""
    if current_user.is_teacher:
        return redirect(url_for('teacher_dashboard'))
    
    enrolled_classes = current_user.enrolled_classes
    return render_template('select_class.html', classes=enrolled_classes)

@app.route('/set_current_class/<int:class_id>')
@login_required
def set_current_class(class_id):
    """Route pour définir la classe actuelle de l'étudiant."""
    if current_user.is_teacher:
        return redirect(url_for('teacher_dashboard'))
    
    # Vérifier que l'étudiant est bien inscrit dans cette classe
    class_ = Class.query.get_or_404(class_id)
    if current_user not in class_.students:
        flash('Vous n\'êtes pas inscrit dans cette classe.', 'danger')
        return redirect(url_for('student_dashboard'))
    
    # Stocker l'ID de la classe dans la session
    session['current_class_id'] = class_id
    return redirect(url_for('view_class', class_id=class_id))

@app.route('/student/join_class', methods=['POST'])
@login_required
def student_join_class():
    """Route pour qu'un étudiant rejoigne une classe avec un code d'invitation."""
    if current_user.is_teacher:
        flash('Seuls les étudiants peuvent rejoindre une classe.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    code = request.form.get('code')
    if not code:
        flash('Le code d\'invitation est requis.', 'danger')
        return redirect(url_for('join_class'))
    
    try:
        # Trouver la classe avec ce code
        class_obj = Class.query.filter_by(invite_code=code).first()
        if not class_obj:
            flash('Code d\'invitation invalide.', 'danger')
            return redirect(url_for('join_class'))
        
        # Vérifier si l'étudiant est déjà inscrit
        if current_user in class_obj.students:
            flash('Vous êtes déjà inscrit dans cette classe.', 'info')
            session['current_class_id'] = class_obj.id
            return redirect(url_for('student_dashboard'))
        
        # Ajouter l'étudiant à la classe
        class_obj.students.append(current_user)
        db.session.commit()
        
        # Définir cette classe comme classe actuelle
        session['current_class_id'] = class_obj.id
        
        flash('Vous avez rejoint la classe avec succès!', 'success')
        return redirect(url_for('student_dashboard'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Erreur lors de l'inscription à la classe: {str(e)}")
        flash('Une erreur est survenue lors de l\'inscription à la classe.', 'danger')
        return redirect(url_for('join_class'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        logger.debug(f"Tentative d'inscription avec : username={form.username.data}, email={form.email.data}, user_type={form.user_type.data}")
        try:
            user = User(
                username=form.username.data,
                email=form.email.data,
                role=form.user_type.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            logger.info(f"Nouvel utilisateur créé : {user.username} (ID: {user.id})")
            
            flash('Inscription réussie! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Erreur lors de l'inscription : {str(e)}")
            db.session.rollback()
            flash('Une erreur est survenue lors de l\'inscription.', 'danger')
    else:
        if form.errors:
            logger.debug(f"Erreurs de validation du formulaire : {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'Erreur dans le champ {field}: {error}', 'danger')
    
    return render_template('register.html', title='Inscription', form=form)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    flash('Vous avez été déconnecté avec succès.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))

@app.route('/teacher_dashboard')
@login_required
@teacher_required
def teacher_dashboard():
    try:
        # Récupérer les classes de l'enseignant
        teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
        
        # Récupérer les exercices créés par l'enseignant
        exercises = Exercise.query.filter_by(created_by=current_user.id).all()
        
        # Calculer les statistiques
        total_classes = len(teacher_classes)
        
        # Calculer le nombre total d'élèves uniques
        student_set = set()
        for class_ in teacher_classes:
            student_set.update([student.id for student in class_.students])
        total_students = len(student_set)
        
        # Calculer le nombre total d'exercices
        total_exercises = len(exercises)
        
        stats = {
            'total_classes': total_classes,
            'total_students': total_students,
            'total_exercises': total_exercises
        }
        
        return render_template('teacher_dashboard.html',
                             classes=teacher_classes,
                             exercises=exercises,
                             stats=stats)
    except Exception as e:
        logger.error(f"Erreur lors de l'accès au tableau de bord enseignant: {str(e)}")
        flash("Une erreur s'est produite lors de l'accès au tableau de bord.", "error")
        return redirect(url_for('index'))

@app.route('/student_dashboard')
@login_required
def student_dashboard():
    """Route pour le tableau de bord étudiant."""
    if current_user.is_teacher:
        return redirect(url_for('teacher_dashboard'))
    
    try:
        # Initialiser le formulaire de jointure de classe
        form = JoinClassForm()
        
        # Si aucune classe n'est sélectionnée, vérifier les classes de l'étudiant
        if 'current_class_id' not in session:
            classes_enrolled = current_user.classes_enrolled
            if not classes_enrolled:
                flash('Vous n\'êtes inscrit à aucune classe. Veuillez en rejoindre une.', 'info')
                return render_template('student_dashboard.html', form=form)
            elif len(classes_enrolled) == 1:
                session['current_class_id'] = classes_enrolled[0].id
            else:
                return redirect(url_for('select_class'))
        
        # Récupérer la classe actuelle
        current_class = Class.query.get(session['current_class_id'])
        if not current_class:
            session.pop('current_class_id', None)
            return render_template('student_dashboard.html', form=form)
        
        # Récupérer les exercices et les soumissions pour la classe actuelle
        class_exercises = []
        
        # Exercices directement dans la classe
        for exercise in current_class.exercises:
            submission = ExerciseSubmission.query.filter_by(
                student_id=current_user.id,
                exercise_id=exercise.id
            ).first()
            exercise.is_completed = submission is not None
            exercise.score = submission.score if submission else None
            class_exercises.append(exercise)
        
        # Exercices des cours
        for course in current_class.courses:
            for exercise in course.exercises:
                submission = ExerciseSubmission.query.filter_by(
                    student_id=current_user.id,
                    exercise_id=exercise.id
                ).first()
                exercise.is_completed = submission is not None
                exercise.score = submission.score if submission else None
                class_exercises.append(exercise)
        
        return render_template('student_dashboard.html',
                            current_class=current_class,
                            exercises=class_exercises,
                            form=form)
    
    except Exception as e:
        app.logger.error(f"Erreur dans student_dashboard: {str(e)}")
        flash("Une erreur s'est produite lors du chargement du tableau de bord.", "error")
        return redirect(url_for('index'))

@app.route('/exercise_library')
@login_required
@teacher_required
def exercise_library():
    try:
        # Récupérer les classes de l'enseignant pour le filtre
        teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
        
        # Récupérer tous les exercices créés par l'enseignant
        exercises = Exercise.query.filter_by(created_by=current_user.id).all()
        
        return render_template('exercise_library.html',
                             exercises=exercises,
                             teacher_classes=teacher_classes)
    except Exception as e:
        logger.error(f"Erreur lors de l'accès à la bibliothèque d'exercices: {str(e)}")
        flash("Une erreur s'est produite lors de l'accès à la bibliothèque.", "error")
        return redirect(url_for('teacher_dashboard'))

@app.route('/create_class', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_class():
    """Route pour créer une nouvelle classe."""
    form = ClassForm()
    if form.validate_on_submit():
        # Créer la nouvelle classe
        new_class = Class(
            name=form.name.data,
            description=form.description.data,
            teacher_id=current_user.id
        )
        db.session.add(new_class)
        db.session.commit()
        
        flash(f'La classe {new_class.name} a été créée avec succès! Code d\'invitation : {new_class.invite_code}', 'success')
        return redirect(url_for('teacher_dashboard'))
        
    return render_template('create_class.html', form=form)

@app.route('/course/create/<int:class_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_course(class_id):
    class_ = Class.query.get_or_404(class_id)
    
    if class_.teacher_id != current_user.id:
        flash('Vous n\'avez pas l\'autorisation de créer un cours dans cette classe.', 'danger')
        return redirect(url_for('teacher_dashboard'))

    form = CourseForm()
    if form.validate_on_submit():
        try:
            course = Course(
                title=form.title.data,
                description=form.description.data,
                content=request.form.get('content', ''),
                class_id=class_id
            )
            db.session.add(course)
            db.session.commit()

            # Gestion des fichiers joints
            if form.files.data:
                course_folder = os.path.join(app.config['UPLOAD_FOLDER'], f'course_{course.id}')
                os.makedirs(course_folder, exist_ok=True)
                
                for file in form.files.data:
                    if file and allowed_file(file.filename):
                        try:
                            filename = secure_filename(file.filename)
                            file_path = os.path.join(course_folder, filename)
                            file.save(file_path)
                            
                            course_file = CourseFile(
                                filename=filename,
                                file_path=file_path,
                                course_id=course.id
                            )
                            db.session.add(course_file)
                        except Exception as e:
                            logger.error(f"Erreur lors de l'upload du fichier {file.filename}: {str(e)}")
                            flash(f'Erreur lors de l\'upload du fichier {file.filename}', 'warning')
                            continue
                    else:
                        flash(f'Le fichier {file.filename} n\'est pas autorisé', 'warning')
                
                try:
                    db.session.commit()
                except Exception as e:
                    logger.error(f"Erreur lors de l'enregistrement des fichiers: {str(e)}")
                    db.session.rollback()
                    flash('Erreur lors de l\'enregistrement des fichiers', 'warning')

            flash(f'Le cours "{form.title.data}" a été créé avec succès.', 'success')
            return redirect(url_for('view_class', class_id=class_id))
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du cours: {str(e)}")
            db.session.rollback()
            flash('Une erreur est survenue lors de la création du cours.', 'danger')

    return render_template('create_course.html', form=form, class_=class_)

@app.route('/create-exercise', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_exercise():
    logger.info("Accès à la route create_exercise")
    form = ExerciseForm()
    
    # Récupérer les classes de l'enseignant
    teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
    logger.info(f"Classes de l'enseignant trouvées: {len(teacher_classes)}")
    
    # Préparer les choix pour le champ course_id
    choices = []
    for class_ in teacher_classes:
        for course in class_.courses:
            choices.append((course.id, f"{class_.name} - {course.title}"))
    form.course_id.choices = choices
    logger.info(f"Nombre de cours disponibles: {len(choices)}")
    
    if request.method == 'POST':
        logger.info("Réception d'une requête POST pour créer un exercice")
        logger.info(f"Données du formulaire reçues: {request.form}")
        logger.info(f"Fichiers reçus: {request.files}")
        
        try:
            # Vérifier les champs requis
            required_fields = ['title', 'course_id', 'exercise_type', 'points']
            for field in required_fields:
                if not request.form.get(field):
                    logger.error(f"Champ requis manquant: {field}")
                    flash(f'Le champ {field} est requis.', 'danger')
                    return render_template('create_exercise.html', form=form, teacher_classes=teacher_classes)
            
            # Créer l'exercice de base
            exercise = Exercise(
                title=request.form['title'],
                description=request.form['description'],
                subject=request.form['subject'],
                level=request.form['level'],
                difficulty=request.form['difficulty'],
                points=int(request.form['points']),
                exercise_type=request.form['exercise_type'],
                course_id=int(request.form['course_id']),
                created_by=current_user.id
            )
            logger.info(f"Exercice créé avec les données de base: {exercise.__dict__}")
            
            exercise_type = request.form['exercise_type']
            logger.info(f"Type d'exercice: {exercise_type}")
            
            if exercise_type == 'QCM':
                # Traiter les questions QCM
                questions = []
                question_texts = request.form.getlist('question_text[]')
                question_images = request.files.getlist('question_image[]')
                
                logger.info(f"Nombre de questions reçues: {len(question_texts)}")
                
                for i in range(len(question_texts)):
                    logger.info(f"Traitement de la question {i}")
                    question_text = question_texts[i]
                    question = Question(text=question_text)
                    
                    # Gérer l'image de la question si présente
                    if i < len(question_images) and question_images[i].filename:
                        image_file = question_images[i]
                        logger.info(f"Image trouvée pour la question {i}: {image_file.filename}")
                        
                        # Créer le dossier uploads s'il n'existe pas
                        upload_folder = os.path.join(app.static_folder, 'uploads')
                        os.makedirs(upload_folder, exist_ok=True)
                        
                        # Sauvegarder l'image
                        filename = secure_filename(image_file.filename)
                        image_path = os.path.join('uploads', filename)
                        full_path = os.path.join(app.static_folder, 'uploads', filename)
                        image_file.save(full_path)
                        question.image = f'uploads/{filename}'
                        logger.info(f"Image sauvegardée: {full_path}")
                    
                    # Traiter les options
                    option_texts = request.form.getlist(f'option_text_{i}[]')
                    correct_answer = request.form.get(f'correct_answer_{i}')
                    
                    logger.info(f"Options pour la question {i}: {option_texts}")
                    logger.info(f"Réponse correcte pour la question {i}: {correct_answer}")
                    
                    # S'assurer que correct_answer est un entier
                    try:
                        correct_answer = int(correct_answer)
                    except (TypeError, ValueError):
                        logger.error(f"Valeur invalide pour correct_answer: {correct_answer}")
                        correct_answer = 0
                    
                    for j, option_text in enumerate(option_texts):
                        is_correct = j == correct_answer
                        logger.info(f"Option {j}: {option_text} (correcte: {is_correct})")
                        choice = Choice(text=option_text, is_correct=is_correct)
                        question.choices.append(choice)
                    
                    questions.append(question)
                
                exercise.questions = questions
                logger.info(f"Total des questions créées: {len(questions)}")
                
            elif exercise_type == 'text_holes':
                # Traiter les trous de texte
                holes = []
                text_before_list = request.form.getlist('text_before[]')
                hole_answers = request.form.getlist('hole_answer[]')
                text_after_list = request.form.getlist('text_after[]')
                hole_images = request.files.getlist('hole_image[]')
                
                logger.info(f"Nombre de trous reçus: {len(hole_answers)}")
                
                for i in range(len(hole_answers)):
                    text_before = text_before_list[i] if i < len(text_before_list) else ''
                    correct_answer = hole_answers[i]
                    text_after = text_after_list[i] if i < len(text_after_list) else ''
                    
                    hole = TextHole(
                        text_before=text_before,
                        correct_answer=correct_answer,
                        text_after=text_after
                    )
                    
                    # Gérer l'image du trou si présente
                    if i < len(hole_images) and hole_images[i].filename:
                        image_file = hole_images[i]
                        logger.info(f"Image trouvée pour le trou {i}: {image_file.filename}")
                        filename = secure_filename(image_file.filename)
                        image_path = os.path.join('uploads', filename)
                        full_path = os.path.join(app.static_folder, 'uploads', filename)
                        image_file.save(full_path)
                        hole.image = image_path
                    
                    holes.append(hole)
                    logger.info(f"Trou {i} créé: {hole.__dict__}")
                
                exercise.text_holes = holes
                logger.info(f"Total des trous créés: {len(holes)}")
            
            elif exercise_type == 'PAIR_MATCH':
                # Traiter les paires d'association
                left_types = request.form.getlist('left_type[]')
                right_types = request.form.getlist('right_type[]')
                left_contents = request.form.getlist('left_content[]')
                right_contents = request.form.getlist('right_content[]')
                
                logger.info(f"Nombre de paires reçues: {len(left_types)}")
                
                for i in range(len(left_types)):
                    left_type = left_types[i]
                    right_type = right_types[i]
                    left_content = ''
                    right_content = ''
                    
                    # Gérer le contenu gauche
                    if left_type == 'text':
                        left_content = left_contents[i]
                    else:  # image
                        if f'left_content_{i}' in request.files:
                            image_file = request.files[f'left_content_{i}']
                            if image_file.filename:
                                filename = secure_filename(image_file.filename)
                                image_path = os.path.join('uploads', filename)
                                full_path = os.path.join(app.static_folder, 'uploads', filename)
                                image_file.save(full_path)
                                left_content = f'uploads/{filename}'
                    
                    # Gérer le contenu droit
                    if right_type == 'text':
                        right_content = right_contents[i]
                    else:  # image
                        if f'right_content_{i}' in request.files:
                            image_file = request.files[f'right_content_{i}']
                            if image_file.filename:
                                filename = secure_filename(image_file.filename)
                                image_path = os.path.join('uploads', filename)
                                full_path = os.path.join(app.static_folder, 'uploads', filename)
                                image_file.save(full_path)
                                right_content = f'uploads/{filename}'
                    
                    pair = PairMatch(
                        left_type=left_type,
                        right_type=right_type,
                        left_content=left_content,
                        right_content=right_content,
                        position=i
                    )
                    exercise.pair_matches.append(pair)
                
                logger.info(f"Total des paires créées: {len(exercise.pair_matches)}")
            
            logger.info("Tentative de sauvegarde dans la base de données")
            db.session.add(exercise)
            db.session.commit()
            
            logger.info(f"Exercice créé avec succès: ID={exercise.id}")
            flash('Exercice créé avec succès!', 'success')
            return redirect(url_for('exercise_library'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la création de l'exercice: {str(e)}")
            logger.exception("Détails de l'erreur:")
            flash('Une erreur est survenue lors de la création de l\'exercice.', 'danger')
            return render_template('create_exercise.html', form=form, teacher_classes=teacher_classes)
    
    return render_template('create_exercise.html', form=form, teacher_classes=teacher_classes)

@app.route('/exercise/<int:exercise_id>/edit_holes', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_holes(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    if not current_user.is_teacher or current_user.id != exercise.course.class_.teacher_id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Supprimer les anciens trous
        for hole in exercise.text_holes:
            db.session.delete(hole)
        db.session.commit()

        # Créer les nouveaux trous
        texts_before = request.form.getlist('text_before[]')
        answers = request.form.getlist('answer[]')
        texts_after = request.form.getlist('text_after[]')

        for i, (text_before, answer, text_after) in enumerate(zip(texts_before, answers, texts_after), 1):
            if text_before.strip() and answer.strip():
                hole = TextHole(
                    text_before=text_before,
                    correct_answer=answer,
                    text_after=text_after,
                    exercise=exercise
                )
                db.session.add(hole)

        db.session.commit()
        log_request_info(request)
        log_form_data(request.form.to_dict(), 'edit_holes')
        logger.info(f"Exercise holes updated successfully for exercise ID: {exercise_id}")
        flash('Exercice à trous mis à jour avec succès!', 'success')
        return redirect(url_for('view_exercise', exercise_id=exercise_id))

    return render_template('edit_holes.html', exercise=exercise)

@app.route('/exercise/<int:exercise_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_exercise(exercise_id):
    try:
        logger.info(f"Tentative de suppression de l'exercice {exercise_id}")
        exercise = Exercise.query.get_or_404(exercise_id)
        
        # Vérifier que l'utilisateur est bien le professeur de la classe
        if exercise.course.class_.teacher_id != current_user.id:
            logger.warning(f"Tentative non autorisée de suppression de l'exercice {exercise_id} par l'utilisateur {current_user.id}")
            flash('Vous n\'avez pas l\'autorisation de supprimer cet exercice.', 'danger')
            return redirect(url_for('view_class', class_id=exercise.course.class_.id))
        
        # Récupérer l'ID de la classe avant de supprimer l'exercice
        class_id = exercise.course.class_id
        
        # Supprimer d'abord les questions et les choix si c'est un QCM
        if exercise.exercise_type == 'qcm':
            logger.info(f"Suppression des questions et choix du QCM {exercise_id}")
            for question in exercise.questions:
                for choice in question.choices:
                    db.session.delete(choice)
                db.session.delete(question)
        
        # Supprimer les trous si c'est un exercice à trous
        elif exercise.exercise_type == 'text_holes':
            logger.info(f"Suppression des trous de l'exercice {exercise_id}")
            for hole in exercise.text_holes:
                db.session.delete(hole)
        
        # Supprimer les paires si c'est un exercice d'association de paires
        elif exercise.exercise_type == 'PAIR_MATCH':
            logger.info(f"Suppression des paires de l'exercice {exercise_id}")
            for pair in exercise.pair_matches:
                db.session.delete(pair)
        
        # Supprimer les soumissions liées à cet exercice
        logger.info(f"Suppression des soumissions de l'exercice {exercise_id}")
        ExerciseSubmission.query.filter_by(exercise_id=exercise_id).delete()
        
        # Supprimer l'exercice
        logger.info(f"Suppression de l'exercice {exercise_id}")
        db.session.delete(exercise)
        db.session.commit()
        
        flash('Exercice supprimé avec succès.', 'success')
        return redirect(url_for('view_class', class_id=class_id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la suppression de l'exercice {exercise_id}: {str(e)}")
        logger.exception("Traceback complet:")
        flash('Une erreur est survenue lors de la suppression de l\'exercice.', 'danger')
        return redirect(url_for('view_class', class_id=class_id))

@app.route('/exercise/<int:exercise_id>/edit/qcm', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_qcm(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    if not current_user.is_teacher:
        flash('Seuls les enseignants peuvent modifier les exercices.', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        try:
            # Supprimer toutes les questions et choix existants
            for question in exercise.questions:
                db.session.delete(question)
            db.session.commit()
            
            # Récupérer tous les champs du formulaire
            form_data = request.form
            
            # Créer un dictionnaire pour stocker les questions et leurs choix
            questions_data = {}
            
            # Parcourir tous les champs du formulaire
            for key, value in form_data.items():
                if key.startswith('question_text_'):
                    question_index = int(key.split('_')[-1])
                    if value.strip():  # Ignorer les questions vides
                        questions_data[question_index] = {
                            'text': value.strip(),
                            'choices': []
                        }
                        
                elif key.startswith('choice_text_'):
                    # Extraire les IDs de la question et du choix
                    question_id, choice_id = key.split('_')[-2:]
                    is_correct = form_data.get(f'is_correct_{question_id}_{choice_id}') == 'on'
                    
                    if value.strip():  # Ignorer les choix vides
                        if question_id not in questions_data:
                            continue
                        
                        questions_data[question_id]['choices'].append({
                            'text': value.strip(),
                            'is_correct': is_correct
                        })
            
            # Créer les nouvelles questions et choix
            for question_index, question_data in questions_data.items():
                question = Question(
                    text=question_data['text'],
                    exercise_id=exercise.id,
                    position=question_index
                )
                db.session.add(question)
                db.session.flush()  # Pour obtenir l'ID de la question
                
                for choice_index, choice_data in enumerate(question_data['choices']):
                    choice = Choice(
                        text=choice_data['text'],
                        is_correct=choice_data['is_correct'],
                        question_id=question.id,
                        position=choice_index
                    )
                    db.session.add(choice)
            
            db.session.commit()
            flash('QCM mis à jour avec succès!', 'success')
            return redirect(url_for('view_exercise', exercise_id=exercise.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour du QCM: {str(e)}', 'danger')
            logger.error(f'Erreur lors de la mise à jour du QCM: {str(e)}')
    
    return render_template('edit_qcm.html', exercise=exercise)

@app.route('/api/filter_exercises')
@login_required
def filter_exercises():
    try:
        logger.info("Début du filtrage des exercices")
        
        # Récupérer les paramètres de filtrage
        subject = request.args.get('subject')
        level = request.args.get('level')
        exercise_type = request.args.get('type')
        
        # Construire la requête de base
        query = Exercise.query
        
        # Appliquer les filtres si présents
        if subject:
            # Gérer à la fois les anciennes et nouvelles catégories
            if '_' in subject:  # Nouvelle catégorie
                query = query.filter(Exercise.subject == subject)
            else:  # Ancienne catégorie
                # Obtenir toutes les sous-catégories correspondantes
                subject_prefix = f"{subject}_"
                query = query.filter(
                    db.or_(
                        Exercise.subject == subject,
                        Exercise.subject.like(f"{subject}_%")
                    )
                )
        
        if level:
            query = query.filter(Exercise.level == level)
            
        if exercise_type:
            query = query.filter(Exercise.exercise_type == exercise_type)
            
        # Exécuter la requête
        exercises = query.all()
        logger.info(f"Nombre d'exercices trouvés: {len(exercises)}")
        
        # Préparer la liste des exercices
        exercise_list = []
        for ex in exercises:
            exercise_data = {
                'id': ex.id,
                'title': ex.title,
                'description': ex.description,
                'subject': get_display_subject(ex.subject),
                'level': ex.level,
                'type': ex.exercise_type,
                'points': ex.points,
                'difficulty': ex.difficulty,
                'created_at': ex.created_at.strftime('%d/%m/%Y') if ex.created_at else None
            }
            exercise_list.append(exercise_data)
            logger.debug(f"Exercice ajouté à la liste: ID={ex.id}, Titre={ex.title}")
        
        return jsonify(exercise_list)
        
    except Exception as e:
        logger.error(f"Erreur lors du filtrage des exercices: {str(e)}")
        return jsonify({'error': 'Une erreur est survenue lors du filtrage des exercices'}), 500

def get_display_subject(subject):
    # Mapping des anciennes catégories vers les nouvelles
    subject_mapping = {
        'mathematiques': 'mathematiques_nombres',
        'francais': 'francais_grammaire',
        'eveil': 'eveil_histoire',
        'sciences': 'sciences_biologie'
    }
    return subject_mapping.get(subject, subject)

@app.route('/exercise/<int:exercise_id>/add_to_class', methods=['POST'])
@login_required
@teacher_required
def add_exercise_to_class(exercise_id):
    if not current_user.is_teacher:
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    class_id = request.args.get('class_id')
    if not class_id:
        return jsonify({'error': 'ID de classe manquant'}), 400
        
    try:
        # Vérifier que l'exercice existe
        exercise = Exercise.query.get_or_404(exercise_id)
        
        # Vérifier que la classe existe et appartient au professeur
        class_obj = Class.query.filter_by(id=class_id, teacher_id=current_user.id).first()
        if not class_obj:
            return jsonify({'error': 'Classe non trouvée ou non autorisée'}), 404
            
        # Vérifier si l'exercice n'est pas déjà dans la classe
        if exercise in class_obj.exercises:
            return jsonify({'message': 'L\'exercice est déjà dans cette classe'})
            
        # Ajouter l'exercice à la classe
        class_obj.exercises.append(exercise)
        db.session.commit()
        
        return jsonify({
            'message': f'Exercice ajouté à la classe {class_obj.name}',
            'exercise_id': exercise_id,
            'class_id': class_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/course/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    class_ = Class.query.get_or_404(course.class_id)
    
    # Vérifier que l'utilisateur est le professeur de cette classe
    if current_user.id != class_.teacher_id:
        flash('Vous n\'avez pas l\'autorisation de modifier ce cours.', 'danger')
        return redirect(url_for('view_class', class_id=class_.id))
    
    form = CourseForm(obj=course)
    
    if form.validate_on_submit():
        course.title = form.title.data
        course.description = form.description.data
        course.content = request.form.get('content', '')
        
        # Gérer les fichiers uploadés
        if 'files' in request.files:
            files = request.files.getlist('files')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    course_folder = os.path.join(app.config['UPLOAD_FOLDER'], f'course_{course_id}')
                    os.makedirs(course_folder, exist_ok=True)
                    
                    file_path = os.path.join(course_folder, filename)
                    file.save(file_path)
                    
                    course_file = CourseFile(
                        filename=filename,
                        file_path=file_path,
                        course_id=course.id
                    )
                    db.session.add(course_file)
            
            db.session.commit()

        log_request_info(request)
        log_form_data(form.data, 'edit_course')
        logger.info(f"Course updated successfully with ID: {course_id}")
        flash('Le cours a été mis à jour avec succès.', 'success')
        return redirect(url_for('view_course', course_id=course.id))
    
    return render_template('create_course.html', form=form, course=course, class_=class_, edit_mode=True)

@app.route('/course/file/<int:file_id>')
@login_required
def download_course_file(file_id):
    file = CourseFile.query.get_or_404(file_id)
    course = file.course
    class_ = course.class_

    # Vérifier si l'utilisateur a accès au fichier
    if current_user.id != class_.teacher_id and current_user not in class_.students:
        flash('Vous n\'avez pas accès à ce fichier.', 'danger')
        return redirect(url_for('student_dashboard'))

    # Construire le chemin du fichier
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
    
    # Vérifier si le fichier existe
    if not os.path.exists(file_path):
        flash('Le fichier n\'existe pas.', 'danger')
        return redirect(url_for('view_course', course_id=course.id))

    # Envoyer le fichier
    return send_file(file_path, as_attachment=True)

@app.route('/course/file/<int:file_id>/view')
@login_required
def view_course_file(file_id):
    file = CourseFile.query.get_or_404(file_id)
    if current_user.id != file.course.teacher_id and not current_user in file.course.students:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('index'))
    
    return send_from_directory(os.path.dirname(file.file_path), os.path.basename(file.file_path))

@app.route('/course/file/<int:file_id>', methods=['DELETE'])
@login_required
@teacher_required
def delete_course_file(file_id):
    file = CourseFile.query.get_or_404(file_id)
    if current_user.id != file.course.teacher_id:
        return jsonify({'error': 'Accès non autorisé'}), 403

    try:
        # Supprimer le fichier physique
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
        
        # Supprimer l'entrée de la base de données
        db.session.delete(file)
        db.session.commit()
        
        log_request_info(request)
        logger.info(f"Course file deleted successfully with ID: {file_id}")
        return jsonify({'message': 'Fichier supprimé avec succès'}), 200
    except Exception as e:
        log_database_error(e, "delete_course_file route")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/courses/<int:course_id>')
@login_required
def view_course(course_id):
    course = Course.query.get_or_404(course_id)
    class_obj = Class.query.get_or_404(course.class_id)
    
    # Vérifier si l'utilisateur a accès au cours
    if not current_user.is_teacher:
        # Pour les étudiants, vérifier s'ils sont dans la liste des étudiants de la classe
        if current_user not in class_obj.students:
            flash('Vous n\'avez pas accès à ce cours.', 'danger')
            return redirect(url_for('student_dashboard'))
    elif class_obj.teacher_id != current_user.id:
        flash('Vous n\'avez pas accès à ce cours.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    # Récupérer les exercices de ce cours
    exercises = Exercise.query.filter_by(course_id=course_id).order_by(Exercise.title).all()
    
    # Récupérer les fichiers attachés au cours
    course_files = CourseFile.query.filter_by(course_id=course_id).all()
    
    return render_template('view_course.html', 
                         course=course,
                         exercises=exercises,
                         course_files=course_files)

@app.route('/courses/<int:course_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_course(course_id):
    # Vérifier le jeton CSRF
    if not request.form.get('csrf_token'):
        logger.warning(f"Tentative de suppression du cours {course_id} sans jeton CSRF")
        flash('Une erreur de sécurité est survenue. Veuillez réessayer.', 'danger')
        return redirect(url_for('view_course', course_id=course_id))

    try:
        logger.info(f"Tentative de suppression du cours {course_id}")
        course = Course.query.get_or_404(course_id)
        
        # Vérifier que l'utilisateur est bien le professeur de la classe
        if course.class_.teacher_id != current_user.id:
            logger.warning(f"Tentative non autorisée de suppression du cours {course_id} par l'utilisateur {current_user.id}")
            flash('Vous n\'êtes pas autorisé à supprimer ce cours.', 'danger')
            return redirect(url_for('view_class', class_id=course.class_id))
        
        # Récupérer l'ID de la classe avant de supprimer le cours
        class_id = course.class_id
        
        # Supprimer d'abord tous les exercices liés au cours
        for exercise in course.exercises:
            # Supprimer les questions et les choix si c'est un QCM
            if exercise.exercise_type == 'qcm':
                logger.info(f"Suppression des questions et choix du QCM {exercise.id}")
                for question in exercise.questions:
                    for choice in question.choices:
                        db.session.delete(choice)
                    db.session.delete(question)
            
            # Supprimer les trous si c'est un exercice à trous
            elif exercise.exercise_type == 'text_holes':
                logger.info(f"Suppression des trous de l'exercice {exercise.id}")
                for hole in exercise.text_holes:
                    db.session.delete(hole)
            
            # Supprimer les paires si c'est un exercice d'association de paires
            elif exercise.exercise_type == 'PAIR_MATCH':
                logger.info(f"Suppression des paires de l'exercice {exercise.id}")
                for pair in exercise.pair_matches:
                    db.session.delete(pair)
            
            # Supprimer les soumissions liées à cet exercice
            logger.info(f"Suppression des soumissions de l'exercice {exercise.id}")
            ExerciseSubmission.query.filter_by(exercise_id=exercise.id).delete()
            
            # Supprimer l'exercice
            logger.info(f"Suppression de l'exercice {exercise.id}")
            db.session.delete(exercise)
        
        # Supprimer les fichiers du cours
        for file in course.files:
            logger.info(f"Suppression du fichier {file.filename}")
            db.session.delete(file)
            # Supprimer le fichier physique
            if os.path.exists(file.file_path):
                os.remove(file.file_path)
        
        # Supprimer le cours
        logger.info(f"Suppression du cours {course_id}")
        db.session.delete(course)
        db.session.commit()
        
        flash('Cours supprimé avec succès.', 'success')
        return redirect(url_for('view_class', class_id=class_id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la suppression du cours {course_id}: {str(e)}")
        logger.exception("Traceback complet:")
        flash('Une erreur est survenue lors de la suppression du cours.', 'danger')
        return redirect(url_for('view_class', class_id=class_id))

@app.route('/exercises/<int:exercise_id>')
@login_required
def view_exercise(exercise_id):
    logger.info(f"Tentative d'accès à l'exercice {exercise_id} par l'utilisateur {current_user.id}")
    
    try:
        # Charger l'exercice avec toutes ses relations
        exercise = Exercise.query.options(
            joinedload(Exercise.questions).joinedload(Question.choices),
            joinedload(Exercise.text_holes),
            joinedload(Exercise.pair_matches),
            joinedload(Exercise.submissions).joinedload(ExerciseSubmission.submitting_student)
        ).get_or_404(exercise_id)
        
        logger.debug(f"Exercice trouvé: ID={exercise.id}, Titre={exercise.title}, Type={exercise.exercise_type}")
        
        # Créer un formulaire vide pour le jeton CSRF
        form = ExerciseForm()
        
        # Mélanger les paires si c'est un exercice de type PAIR_MATCH
        if exercise.exercise_type == 'PAIR_MATCH':
            import random
            pair_matches = list(exercise.pair_matches)
            random.shuffle(pair_matches)
            exercise.pair_matches = pair_matches
        
        # Vérifier si l'utilisateur est inscrit au cours
        is_enrolled = False
        if not current_user.is_teacher:
            enrollment = ClassEnrollment.query.filter_by(
                student_id=current_user.id,
                class_id=exercise.course.class_.id
            ).first()
            is_enrolled = enrollment is not None
        
        # Récupérer la dernière soumission de l'utilisateur
        user_submission = None
        if not current_user.is_teacher:
            user_submission = ExerciseSubmission.query.filter_by(
                student_id=current_user.id,
                exercise_id=exercise_id
            ).order_by(ExerciseSubmission.submitted_at.desc()).first()
        
        # Récupérer toutes les soumissions si c'est un enseignant
        submissions = None
        if current_user.role == 'teacher':
            teacher_classes = Class.query.filter_by(teacher_id=current_user.id).with_entities(Class.id).all()
            teacher_class_ids = [c.id for c in teacher_classes]
            submissions = ExerciseSubmission.query.filter_by(
                exercise_id=exercise_id
            ).join(User, User.id == ExerciseSubmission.student_id)\
             .join(ClassEnrollment, ClassEnrollment.student_id == User.id)\
             .filter(ClassEnrollment.class_id.in_(teacher_class_ids))\
             .order_by(ExerciseSubmission.submitted_at.desc()).all()
        
        is_teacher = current_user.role == 'teacher'
        
        return render_template('view_exercise.html',
                          exercise=exercise,
                          questions=exercise.questions if exercise.exercise_type == 'QCM' else None,
                          text_holes=exercise.text_holes if exercise.exercise_type == 'text_holes' else None,
                          pair_matches=exercise.pair_matches if exercise.exercise_type == 'PAIR_MATCH' else None,
                          is_teacher=is_teacher,
                          is_enrolled=is_enrolled,
                          user_submission=user_submission,
                          submissions=submissions,
                          form=form)
                          
    except Exception as e:
        logger.error(f"Erreur lors de l'accès à l'exercice {exercise_id}: {str(e)}")
        flash("Une erreur s'est produite lors du chargement de l'exercice.", 'danger')
        return redirect(url_for('exercise_library'))

@app.route('/submit_exercise/<int:exercise_id>', methods=['POST'])
def submit_exercise(exercise_id):
    try:
        logger.info(f"Tentative de soumission pour l'exercice {exercise_id}")
        exercise = Exercise.query.get_or_404(exercise_id)
        
        # Trouver la classe associée à l'exercice
        target_class = None
        
        # Si l'exercice est dans un cours
        if exercise.course:
            target_class = exercise.course.class_
        else:
            # Chercher dans les classes où l'exercice est directement ajouté
            for class_ in current_user.enrolled_classes:
                if exercise in class_.exercises:
                    target_class = class_
                    break
        
        # Vérifier si l'étudiant a déjà soumis cet exercice
        existing_submission = ExerciseSubmission.query.filter_by(
            exercise_id=exercise_id,
            student_id=current_user.id
        ).first()
        
        if existing_submission:
            flash('Vous avez déjà soumis cet exercice.', 'warning')
            if target_class:
                return redirect(url_for('view_class', class_id=target_class.id))
            else:
                return redirect(url_for('student_dashboard'))
        
        answers = {}
        score = None
        if exercise.exercise_type == 'QCM':
            total_questions = len(exercise.questions)
            correct_answers = 0
            
            for question in exercise.questions:
                answer_key = f'answer_{question.id}'
                selected_choice_id = request.form.get(answer_key)
                
                if selected_choice_id:
                    answers[str(question.id)] = selected_choice_id
                    selected_choice = Choice.query.get(selected_choice_id)
                    if selected_choice and selected_choice.is_correct:
                        correct_answers += 1
            
            if total_questions > 0:
                score = (correct_answers / total_questions)
                
        elif exercise.exercise_type == 'text_holes':
            total_holes = len(exercise.text_holes)
            correct_answers = 0
            student_answers = []
            
            for i, hole in enumerate(exercise.text_holes):
                answer_key = f'answer_{i}'
                student_answer = request.form.get(answer_key, '').strip()
                student_answers.append(student_answer)
                
                if student_answer.lower() == hole.correct_answer.lower():
                    correct_answers += 1
            
            answers = student_answers
            if total_holes > 0:
                score = (correct_answers / total_holes)
                
        elif exercise.exercise_type == 'PAIR_MATCH':
            matches_json = request.form.get('matches', '[]')
            try:
                matches = json.loads(matches_json)
                total_pairs = len(exercise.pair_matches)
                correct_matches = 0
                
                for match in matches:
                    left_id = str(match.get('left'))
                    right_id = str(match.get('right'))
                    
                    if left_id and right_id:
                        answers[left_id] = right_id
                        pair = PairMatch.query.get(left_id)
                        if pair and str(pair.id) == right_id:
                            correct_matches += 1
                
                if total_pairs > 0:
                    score = (correct_matches / total_pairs)
            except json.JSONDecodeError:
                flash('Format de réponse invalide.', 'error')
                if target_class:
                    return redirect(url_for('view_class', class_id=target_class.id))
                else:
                    return redirect(url_for('student_dashboard'))
        
        # Calculer le score final en points
        final_score = score * exercise.points
        
        # Créer et sauvegarder la soumission
        submission = ExerciseSubmission(
            student_id=current_user.id,
            exercise_id=exercise_id,
            answers=json.dumps(answers),
            score=score,  # Sauvegarder le score en pourcentage (0-1)
            submitted_at=datetime.utcnow()
        )
        
        db.session.add(submission)
        db.session.commit()
        
        # Afficher le score en pourcentage pour l'utilisateur
        percentage = score * 100
        flash(f'Exercice soumis avec succès ! Score : {percentage:.1f}% ({final_score:.1f}/{exercise.points} points)', 'success')
        
        # Rediriger vers la classe si possible, sinon vers le tableau de bord
        if target_class:
            return redirect(url_for('view_class', class_id=target_class.id))
        else:
            return redirect(url_for('student_dashboard'))
            
    except Exception as e:
        db.session.rollback()
        log_database_error(e, f"Erreur lors de la soumission de l'exercice {exercise_id}")
        flash("Une erreur s'est produite lors de la soumission de l'exercice.", 'error')
        return redirect(url_for('view_exercise', exercise_id=exercise_id))

@app.route('/exercises/<int:exercise_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_exercise(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    course = Course.query.get_or_404(exercise.course_id)
    class_ = Class.query.get_or_404(course.class_id)
    
    # Vérifier que l'utilisateur est le professeur de la classe
    if current_user.id != class_.teacher_id:
        flash('Vous n\'êtes pas autorisé à modifier cet exercice.', 'danger')
        return redirect(url_for('view_exercise', exercise_id=exercise.id))
    
    form = ExerciseForm(obj=exercise)
    
    # Définir les choix pour le champ course_id
    teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
    available_courses = []
    for teacher_class in teacher_classes:
        courses = Course.query.filter_by(class_id=teacher_class.id).all()
        available_courses.extend(courses)
    
    form.course_id.choices = [(c.id, f"{c.title} ({c.class_.name})") for c in available_courses]
    
    if form.validate_on_submit():
        try:
            # Mettre à jour les informations de base
            exercise.title = form.title.data
            exercise.description = form.description.data
            exercise.difficulty = form.difficulty.data
            exercise.points = form.points.data
            exercise.subject = form.subject.data
            exercise.level = form.level.data
            
            # Gérer l'upload d'image
            if form.image.data:
                try:
                    image_filename = secure_filename(form.image.data.filename)
                    exercise_folder = os.path.join(app.config['UPLOAD_FOLDER'], f'exercises/{exercise_id}')
                    os.makedirs(exercise_folder, exist_ok=True)
                    
                    image_filepath = os.path.join(exercise_folder, image_filename)
                    form.image.data.save(image_filepath)
                    exercise.image_path = f'uploads/exercises/{exercise_id}/{image_filename}'
                except Exception as e:
                    logger.error(f"Error saving image: {str(e)}")
                    flash('Erreur lors de l\'enregistrement de l\'image', 'danger')
            
            # Supprimer les anciennes questions/choix ou trous
            if exercise.exercise_type == 'qcm':
                for question in exercise.questions:
                    db.session.delete(question)
                
                # Ajouter les nouvelles questions et choix
                for question_data in form.questions.data:
                    if question_data.get('text'):
                        question = Question(
                            text=question_data['text'],
                            exercise_id=exercise.id
                        )
                        db.session.add(question)
                        db.session.flush()  # Pour obtenir l'ID de la question
                        
                        for choice_data in question_data['choices']:
                            if choice_data.get('text'):
                                choice = Choice(
                                    text=choice_data['text'],
                                    is_correct=choice_data.get('is_correct', False),
                                    question_id=question.id
                                )
                                db.session.add(choice)
            
            elif exercise.exercise_type == 'text_holes':
                for hole in exercise.text_holes:
                    db.session.delete(hole)
                
                # Ajouter les nouveaux trous
                for i, hole_data in enumerate(form.text_holes.data):
                    if hole_data.get('text_before') and hole_data.get('correct_answer'):
                        text_hole = TextHole(
                            text_before=hole_data['text_before'],
                            correct_answer=hole_data['correct_answer'],
                            text_after=hole_data.get('text_after', ''),
                            exercise_id=exercise.id
                        )
                        db.session.add(text_hole)
            
            elif exercise.exercise_type == 'PAIR_MATCH':
                for pair in exercise.pair_matches:
                    db.session.delete(pair)
                
                # Ajouter les nouvelles paires
                for i, pair_data in enumerate(form.pair_matches.data):
                    if pair_data.get('left_type') and pair_data.get('right_type'):
                        pair_match = PairMatch(
                            left_type=pair_data['left_type'],
                            right_type=pair_data['right_type'],
                            left_content=pair_data.get('left_content', ''),
                            right_content=pair_data.get('right_content', ''),
                            exercise_id=exercise.id
                        )
                        db.session.add(pair_match)
            
            db.session.commit()
            logger.info(f"Exercise updated successfully with ID: {exercise_id}")
            flash('Exercice mis à jour avec succès!', 'success')
            return redirect(url_for('view_exercise', exercise_id=exercise.id))
            
        except Exception as e:
            logger.error(f"Error updating exercise: {str(e)}")
            db.session.rollback()
            flash('Erreur lors de la mise à jour de l\'exercice', 'danger')
    
    if form.errors:
        logger.debug(f"Form validation errors: {form.errors}")
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Erreur dans le champ {field}: {error}', 'danger')
    
    # Pré-remplir le formulaire avec les données existantes
    if request.method == 'GET':
        form.title.data = exercise.title
        form.description.data = exercise.description
        form.difficulty.data = exercise.difficulty
        form.points.data = exercise.points
        form.subject.data = exercise.subject
        form.level.data = exercise.level
        
        if exercise.exercise_type == 'qcm':
            form.questions.entries = []
            for question in exercise.questions:
                question_form = QuestionForm()
                question_form.text.data = question.text
                
                choices = []
                for choice in question.choices:
                    choice_form = ChoiceForm()
                    choice_form.text.data = choice.text
                    choice_form.is_correct.data = choice.is_correct
                    choices.append(choice_form)
                
                # Ajouter des choix vides si nécessaire
                while len(choices) < 4:
                    choices.append(ChoiceForm())
                
                question_form.choices = choices
                form.questions.append_entry(question_form)
        
        elif exercise.exercise_type == 'text_holes':
            form.text_holes.entries = []
            for hole in exercise.text_holes:
                hole_form = TextHoleForm()
                hole_form.text_before.data = hole.text_before
                hole_form.correct_answer.data = hole.correct_answer
                hole_form.text_after.data = hole.text_after
                form.text_holes.append_entry(hole_form)
        
        elif exercise.exercise_type == 'PAIR_MATCH':
            form.pair_matches.entries = []
            for pair in exercise.pair_matches:
                pair_form = PairMatchForm()
                pair_form.left_type.data = pair.left_type
                pair_form.right_type.data = pair.right_type
                
                if pair.left_type == 'text':
                    pair_form.left_content.data = pair.left_content
                if pair.right_type == 'text':
                    pair_form.right_content.data = pair.right_content
                
                form.pair_matches.append_entry(pair_form)
            
            # Add an empty pair form if there are no pairs
            if not exercise.pair_matches:
                form.pair_matches.append_entry(PairMatchForm())
    
    return render_template('edit_exercise.html', form=form, exercise=exercise)

from forms import GradeForm

@app.route('/grade_submission/<int:exercise_id>/<int:submission_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def grade_submission(exercise_id, submission_id):
    submission = ExerciseSubmission.query.get_or_404(submission_id)
    exercise = Exercise.query.get_or_404(exercise_id)
    
    # Vérifier que l'enseignant est bien le propriétaire de l'exercice
    if exercise.course.class_.teacher_id != current_user.id:
        flash('Vous n\'êtes pas autorisé à noter cet exercice.', 'danger')
        return redirect(url_for('index'))

    form = GradeForm()
    
    if form.validate_on_submit():
        submission.score = form.score.data
        submission.feedback = form.feedback.data
        db.session.commit()
        flash('Note enregistrée avec succès!', 'success')
        return redirect(url_for('view_exercise', exercise_id=exercise_id))

    # Pré-remplir le formulaire avec les valeurs existantes
    if submission.score is not None:
        form.score.data = submission.score
    if hasattr(submission, 'feedback') and submission.feedback:
        form.feedback.data = submission.feedback

    # Pour un QCM, calculer le score automatiquement
    if exercise.exercise_type == 'qcm':
        correct_answers = 0
        total_questions = len(exercise.questions)
        
        for question in exercise.questions:
            answer_key = f'question_{question.id}'
            if answer_key in submission.answers:
                student_choice = submission.answers[answer_key]
                correct_choice = next((choice for choice in question.choices if choice.is_correct), None)
                if correct_choice and student_choice == correct_choice.id:
                    correct_answers += 1
        
        suggested_score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        if submission.score is None:
            form.score.data = suggested_score

    return render_template('grade_submission.html', 
                         exercise=exercise, 
                         submission=submission, 
                         form=form)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', title='Mon Profil')

@app.route('/classes/<int:class_id>')
@login_required
def view_class(class_id):
    class_ = Class.query.get_or_404(class_id)
    
    # Vérifier si l'utilisateur est autorisé à voir cette classe
    if not current_user.is_teacher:
        # Pour les étudiants, vérifier s'ils sont inscrits dans la classe
        enrollment = ClassEnrollment.query.filter_by(
            student_id=current_user.id,
            class_id=class_id
        ).first()
        if not enrollment:
            flash('Vous n\'êtes pas inscrit dans cette classe.', 'danger')
            return redirect(url_for('student_dashboard'))
    elif class_.teacher_id != current_user.id:
        flash('Vous n\'êtes pas l\'enseignant de cette classe.', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    # Récupérer tous les cours de la classe
    courses = Course.query.filter_by(class_id=class_id).all()
    
    # Récupérer les exercices pour chaque cours
    course_exercises = {}
    total_course_exercises = 0
    for course in courses:
        exercises = Exercise.query.filter_by(course_id=course.id).all()
        course_exercises[course.id] = exercises
        total_course_exercises += len(exercises)
    
    # Récupérer les exercices directement liés à la classe
    class_exercises = class_.exercises.all()
    
    # Calculer le nombre total d'exercices
    total_exercises = len(class_exercises) + total_course_exercises
    
    # Récupérer les étudiants inscrits
    enrolled_students = User.query.join(ClassEnrollment).filter(ClassEnrollment.class_id == class_id).all()
    
    return render_template('view_class.html', 
                         class_=class_,
                         courses=courses,
                         course_exercises=course_exercises,
                         class_exercises=class_exercises,
                         total_exercises=total_exercises,
                         enrolled_students=enrolled_students,
                         title=class_.name)

@app.route('/class/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_class(class_id):
    class_ = Class.query.get_or_404(class_id)
    if not current_user.is_teacher or class_.teacher != current_user:
        flash('Vous n\'avez pas la permission de modifier cette classe.', 'danger')
        return redirect(url_for('index'))
    
    form = ClassForm()
    if form.validate_on_submit():
        class_.name = form.name.data
        class_.description = form.description.data
        db.session.commit()
        log_request_info(request)
        log_form_data(request.form.to_dict(), 'edit_class')
        logger.info(f"Class updated successfully with ID: {class_id}")
        flash('La classe a été mise à jour avec succès!', 'success')
        return redirect(url_for('view_class', class_id=class_.id))
    elif request.method == 'GET':
        form.name.data = class_.name
        form.description.data = class_.description
    
    return render_template('edit_class.html', title='Modifier la Classe', form=form, class_=class_)

@app.route('/class/<int:class_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_class(class_id):
    if not current_user.is_teacher:
        flash('Seuls les enseignants peuvent supprimer des classes.', 'danger')
        return redirect(url_for('index'))

    class_ = Class.query.get_or_404(class_id)
    
    if class_.teacher_id != current_user.id:
        flash('Vous n\'avez pas l\'autorisation de supprimer cette classe.', 'danger')
        return redirect(url_for('teacher_dashboard'))

    try:
        # Supprimer le dossier des fichiers de la classe s'il existe
        class_folder = os.path.join(app.config['UPLOAD_FOLDER'], f'class_{class_id}')
        if os.path.exists(class_folder):
            shutil.rmtree(class_folder)
        
        # Supprimer la classe de la base de données
        db.session.delete(class_)
        db.session.commit()
        
        log_request_info(request)
        logger.info(f"Class deleted successfully with ID: {class_id}")
        flash('La classe a été supprimée avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la suppression de la classe {class_id}: {str(e)}")
        flash('Une erreur est survenue lors de la suppression de la classe.', 'danger')
        app.logger.error(f'Erreur lors de la suppression de la classe {class_id}: {str(e)}')

    return redirect(url_for('teacher_dashboard'))

@app.route('/class/<int:class_id>/remove-student/<int:student_id>', methods=['POST'])
@login_required
@teacher_required
def remove_student_from_class(class_id, student_id):
    if current_user.role != 'teacher':
        flash('Seuls les enseignants peuvent retirer des étudiants.', 'danger')
        return redirect(url_for('view_class', class_id=class_id))
    
    class_obj = Class.query.get_or_404(class_id)
    if class_obj.teacher_id != current_user.id:
        flash('Vous n\'êtes pas l\'enseignant de cette classe.', 'danger')
        return redirect(url_for('view_class', class_id=class_id))
    
    enrollment = ClassEnrollment.query.filter_by(
        student_id=student_id,
        class_id=class_id
    ).first_or_404()
    
    try:
        db.session.delete(enrollment)
        db.session.commit()
        log_request_info(request)
        logger.info(f"Student removed from class with ID: {class_id}")
        flash('Étudiant retiré de la classe avec succès.', 'success')
    except Exception as e:
        log_database_error(e, "remove_student_from_class route")
        db.session.rollback()
        flash('Erreur lors de la suppression de l\'étudiant.', 'danger')
        print(f"Error removing student: {str(e)}")
    
    return redirect(url_for('view_class', class_id=class_id))

@app.route('/course/<int:course_id>/upload-file', methods=['POST'])
@login_required
@teacher_required
def upload_course_file(course_id):
    course = Course.query.get_or_404(course_id)
    class_ = course.class_

    if current_user.id != class_.teacher_id:
        flash('Vous n\'êtes pas autorisé à télécharger des fichiers pour ce cours.', 'danger')
        return redirect(url_for('view_course', course_id=course_id))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Aucun fichier n\'a été sélectionné.', 'danger')
            return redirect(url_for('view_course', course_id=course_id))

        file = request.files['file']
        if file.filename == '':
            flash('Aucun fichier n\'a été sélectionné.', 'danger')
            return redirect(url_for('view_course', course_id=course_id))

        if file:
            filename = secure_filename(file.filename)
            unique_filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            try:
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(file_path)
                
                course_file = CourseFile(
                    filename=unique_filename,
                    file_path=file_path,
                    course_id=course_id
                )
                db.session.add(course_file)
                db.session.commit()
                
                flash('Fichier téléchargé avec succès.', 'success')
                return redirect(url_for('view_course', course_id=course_id))
            except Exception as e:
                app.logger.error(f"Erreur lors du téléchargement du fichier : {str(e)}")
                flash('Une erreur est survenue lors du téléchargement du fichier.', 'danger')
                return redirect(request.url)

    return render_template('upload_course_file.html', course=course)

@app.route('/upload/image/<int:course_id>', methods=['POST'])
@login_required
@teacher_required
def upload_image(course_id):
    # CKEditor envoie le fichier avec le paramètre 'upload'
    if 'upload' not in request.files and 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier n\'a été envoyé'}), 400
    
    # Accepter soit 'upload' (CKEditor) soit 'file' (formulaire standard)
    file = request.files.get('upload') or request.files.get('file')
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
        
    if file and allowed_file(file.filename, {'png', 'jpg', 'jpeg', 'gif'}):
        # Générer un nom de fichier unique
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'images', unique_filename)
        
        # Créer le dossier images s'il n'existe pas
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        file.save(file_path)
        
        # Créer une nouvelle image dans la base de données
        image = Image(
            filename=unique_filename,
            course_id=course_id,
            path=f'uploads/images/{unique_filename}'
        )
        db.session.add(image)
        db.session.commit()
        
        # Retourner l'URL de l'image dans le format attendu par CKEditor
        return jsonify({
            'url': url_for('static', filename=f'uploads/images/{unique_filename}', _external=True)
        })
    
    return jsonify({'error': 'Type de fichier non autorisé'}), 400

@app.route('/exercises/<int:exercise_id>/image')
@login_required
def view_exercise_image(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    if not exercise.image_path:
        return jsonify({'error': 'Aucune image trouvée'}), 404
    
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], exercise.image_path)
    if not os.path.exists(image_path):
        return jsonify({'error': 'Image non trouvée'}), 404
    
    return send_from_directory(os.path.dirname(image_path), os.path.basename(image_path))

@app.route('/create_polygon_exercise/<int:course_id>')
@login_required
@teacher_required
def create_polygon_exercise(course_id):
    try:
        # Créer un nouvel exercice
        exercise = Exercise(
            title='Le nom des polygones',
            description='Complète avec la bonne étiquette.',
            exercise_type='mots_a_placer',
            difficulty='facile',
            points=10,
            course_id=course_id,
            created_date=datetime.utcnow(),
            teacher_id=current_user.id,  # Ajout du teacher_id
            is_in_library=True
        )
        
        db.session.add(exercise)
        db.session.commit()
        
        flash('Exercice sur les polygones créé avec succès!', 'success')
        return redirect(url_for('view_course', course_id=course_id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la création de l'exercice: {str(e)}")
        flash('Erreur lors de la création de l\'exercice.', 'danger')
        return redirect(url_for('view_course', course_id=course_id))

@app.route('/delete_student/<int:student_id>', methods=['POST'])
@login_required
@teacher_required
def delete_student(student_id):
    try:
        # Supprimer d'abord les soumissions de l'étudiant
        ExerciseSubmission.query.filter_by(student_id=student_id).delete()
        
        # Supprimer les inscriptions aux classes
        ClassEnrollment.query.filter_by(student_id=student_id).delete()
        
        # Supprimer l'utilisateur
        student = User.query.get_or_404(student_id)
        db.session.delete(student)
        db.session.commit()
        
        flash('Étudiant supprimé avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la suppression de l\'étudiant.', 'danger')
        logger.error(f"Erreur lors de la suppression de l'étudiant {student_id}: {str(e)}")
    
    return redirect(url_for('manage_students'))

@app.route("/debug/exercises")
@login_required
def debug_exercises():
    exercises = Exercise.query.all()
    result = []
    for ex in exercises:
        result.append({
            "id": ex.id,
            "title": ex.title,
            "created_by": ex.created_by,
            "course_id": ex.course_id
        })
    return jsonify(result)

@app.route("/debug/exercise/<int:exercise_id>")
@login_required
def debug_exercise(exercise_id):
    exercise = Exercise.query.get(exercise_id)
    if exercise is None:
        return jsonify({
            "exists": False,
            "message": "Exercise not found"
        })
    return jsonify({
        "exists": True,
        "id": exercise.id,
        "title": exercise.title,
        "created_by": exercise.created_by,
        "course_id": exercise.course_id
    })

@app.route('/debug/submissions/<int:exercise_id>')
@login_required
def debug_submissions(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    submissions = ExerciseSubmission.query.filter_by(exercise_id=exercise_id).all()
    
    debug_info = {
        'exercise_id': exercise_id,
        'exercise_type': exercise.exercise_type,
        'submissions': []
    }
    
    for submission in submissions:
        sub_info = {
            'id': submission.id,
            'student': submission.submitting_student.username,
            'submitted_at': submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S'),
            'score': submission.score,
            'answers': submission.answers
        }
        debug_info['submissions'].append(sub_info)
    
    return jsonify(debug_info)

@app.route('/exercise_stats')
@login_required
@teacher_required
def exercise_stats():
    """Route pour afficher les statistiques des exercices."""
    try:
        # Récupérer toutes les classes de l'enseignant
        teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
        
        # Dictionnaire pour stocker les statistiques par exercice et par classe
        exercise_stats_dict = {}
        total_submissions = 0
        
        # Pour chaque classe de l'enseignant
        for class_ in teacher_classes:
            # Récupérer tous les exercices de la classe (cours + directs)
            class_exercises = set()
            
            # Ajouter les exercices des cours
            for course in class_.courses:
                class_exercises.update(course.exercises)
            
            # Ajouter les exercices directement liés à la classe
            class_exercises.update(class_.exercises)
            
            # Pour chaque exercice dans cette classe
            for exercise in class_exercises:
                # Récupérer les soumissions des étudiants de cette classe pour cet exercice
                submissions = ExerciseSubmission.query.join(
                    User, ExerciseSubmission.student_id == User.id
                ).filter(
                    ExerciseSubmission.exercise_id == exercise.id,
                    User.id.in_([student.id for student in class_.students])
                ).all()
                
                if not submissions:
                    continue
                
                # Clé unique pour l'exercice dans cette classe
                stats_key = (exercise.id, class_.id)
                
                # Si c'est la première fois qu'on voit cet exercice dans cette classe
                if stats_key not in exercise_stats_dict:
                    submissions_with_details = []
                    scores = []
                    
                    for submission in submissions:
                        if submission.score is not None:
                            score = float(submission.score)
                            scores.append(score)
                            submissions_with_details.append({
                                'student_name': submission.submitting_student.username,
                                'score': score,
                                'submitted_at': submission.submitted_at
                            })
                    
                    if scores:  # S'il y a des scores valides
                        avg_score = sum(scores) / len(scores)
                        exercise_stats_dict[stats_key] = {
                            'exercise': exercise,
                            'class_name': class_.name,
                            'submissions': submissions_with_details,
                            'submissions_count': len(submissions),
                            'average_score': avg_score
                        }
                        total_submissions += len(submissions)
        
        # Convertir le dictionnaire en liste pour l'affichage
        exercise_stats = list(exercise_stats_dict.values())
        
        # Calculer la moyenne globale
        all_scores = [stat['average_score'] for stat in exercise_stats if 'average_score' in stat]
        overall_average = sum(all_scores) / len(all_scores) if all_scores else 0
        
        overall_stats = {
            'total_exercises': len(exercise_stats_dict),
            'total_submissions': total_submissions,
            'average_score': overall_average
        }
        
        return render_template('exercise_stats.html', 
                             exercise_stats=exercise_stats,
                             overall_stats=overall_stats)
                             
    except Exception as e:
        app.logger.error(f"Erreur dans exercise_stats: {str(e)}")
        flash("Une erreur s'est produite lors du chargement des statistiques.", "danger")
        return redirect(url_for('teacher_dashboard'))

@app.route('/exercise/<int:exercise_id>/stats')
@login_required
@teacher_required
def exercise_specific_stats(exercise_id):
    """Route pour afficher les statistiques d'un exercice spécifique."""
    try:
        exercise = Exercise.query.get_or_404(exercise_id)
        
        # Vérifier que l'enseignant a accès à cet exercice
        if exercise.course.class_.teacher_id != current_user.id:
            flash("Vous n'avez pas accès à ces statistiques.", "error")
            return redirect(url_for('teacher_dashboard'))
            
        # Récupérer toutes les soumissions pour cet exercice avec une jointure sur la table User
        submissions = db.session.query(
            ExerciseSubmission,
            User
        ).join(
            User,
            ExerciseSubmission.student_id == User.id
        ).filter(
            ExerciseSubmission.exercise_id == exercise_id
        ).all()
        
        submissions_with_details = []
        scores = []
        
        for submission, user in submissions:
            if submission.score is not None:
                scores.append(float(submission.score))
                submissions_with_details.append({
                    'student_name': user.username,
                    'score': float(submission.score),
                    'submitted_at': submission.submitted_at
                })
        
        num_submissions = len(submissions)
        avg_score = sum(scores) / len(scores) if scores else 0
        
        exercise_stats = [{
            'exercise': exercise,
            'submissions': submissions_with_details,
            'submissions_count': num_submissions,
            'average_score': avg_score,
            'class_name': exercise.course.class_.name
        }]
        
        overall_stats = {
            'total_exercises': 1,  # Un seul exercice
            'total_submissions': num_submissions,
            'average_score': avg_score
        }
        
        return render_template('exercise_stats.html',
                            exercise_stats=exercise_stats,
                            overall_stats=overall_stats,
                            single_exercise=True)
    except Exception as e:
        log_database_error(e, f"Erreur lors de l'accès aux statistiques de l'exercice {exercise_id}")
        flash("Une erreur s'est produite lors de l'accès aux statistiques.", "error")
        return redirect(url_for('view_exercise', exercise_id=exercise_id))

@app.route('/uploads/<path:filename>')
@login_required
def serve_upload(filename):
    """Sert les fichiers uploadés de manière sécurisée."""
    try:
        # Nettoyer le chemin du fichier
        if filename.startswith('uploads/'):
            clean_filename = filename[8:]  # Enlever 'uploads/'
        else:
            clean_filename = filename
            
        clean_filename = clean_filename.replace('\\', '/').strip('/')
        logger.info(f"Tentative d'accès au fichier: {clean_filename}")
        
        # Construire le chemin complet vers le fichier
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'uploads')
        file_path = os.path.join(upload_folder, clean_filename)
        logger.info(f"Chemin complet du fichier: {file_path}")
        
        # Vérifier que le fichier existe
        if os.path.exists(file_path):
            logger.info(f"Fichier trouvé, envoi de: {clean_filename}")
            try:
                response = send_from_directory(upload_folder, clean_filename)
                logger.info("Fichier envoyé avec succès")
                return response
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi du fichier: {str(e)}")
                raise
        else:
            # Essayer de trouver le fichier dans le dossier uploads
            all_files = os.listdir(upload_folder)
            logger.error(f"Fichier non trouvé: {file_path}")
            logger.info(f"Fichiers disponibles dans {upload_folder}: {all_files}")
            abort(404)
    except Exception as e:
        logger.error(f"Erreur lors de l'accès au fichier {filename}: {str(e)}")
        abort(404)

@app.route('/join_class', methods=['GET', 'POST'])
@login_required
def join_class():
    """Route pour qu'un étudiant rejoigne une classe."""
    if current_user.is_teacher:
        flash('Les enseignants ne peuvent pas rejoindre de classe.', 'warning')
        return redirect(url_for('teacher_dashboard'))

    form = JoinClassForm()
    if form.validate_on_submit():
        try:
            # Vérifier si le code d'invitation est valide
            class_obj = Class.query.filter_by(invite_code=form.code.data).first()
            if not class_obj:
                flash('Code d\'invitation invalide.', 'danger')
                return render_template('join_class.html', form=form)
            
            # Vérifier si l'étudiant est déjà inscrit
            if current_user in class_obj.students:
                flash('Vous êtes déjà inscrit dans cette classe.', 'info')
                session['current_class_id'] = class_obj.id
                return redirect(url_for('student_dashboard'))
            
            # Ajouter l'étudiant à la classe
            class_obj.students.append(current_user)
            db.session.commit()
            
            # Définir cette classe comme classe actuelle
            session['current_class_id'] = class_obj.id
            
            flash('Vous avez rejoint la classe avec succès!', 'success')
            return redirect(url_for('student_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur lors de l'inscription à la classe: {str(e)}")
            flash('Une erreur est survenue lors de l\'inscription à la classe.', 'danger')
            return render_template('join_class.html', form=form)
    
    return render_template('join_class.html', form=form)

if __name__ == '__main__':
    with app.app_context():
        # Créer les tables si elles n'existent pas
        db.create_all()
        
        # Créer un utilisateur enseignant par défaut si aucun n'existe
        if not User.query.filter_by(role='teacher').first():
            teacher = User(
                username='Prof. Mr Zahiri',
                email='zahiri@example.com',
                role='teacher'
            )
            teacher.set_password('password123')
            db.session.add(teacher)
            db.session.commit()
            
        # Démarrer l'application
        app.run(debug=True)
