from flask import Flask, render_template, url_for, flash, redirect, request, jsonify, send_from_directory, abort, session
from flask_login import login_user, current_user, logout_user, login_required
from extensions import db, migrate, bcrypt, login_manager, csrf
from datetime import datetime, timezone, timedelta
from functools import wraps
import os
import json
import logging
from logging.handlers import RotatingFileHandler

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'classe_numerique.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit
    
    # Configuration des sessions et cookies
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)
    app.config['REMEMBER_COOKIE_SECURE'] = False  # Mettre à True en production
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    
    # Configuration du dossier d'upload
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # Initialisation des extensions
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'info'
    
    # Import des modèles et des formulaires (après l'initialisation des extensions)
    from models import User, Class, Course, Exercise, ExerciseSubmission, ClassEnrollment, Question, Choice
    from forms import (LoginForm, RegistrationForm, ClassForm, CourseForm, 
                      ExerciseForm, GradeForm, TextHoleForm, QuestionForm, ChoiceForm,
                      PairMatchForm, JoinClassForm)
    
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    logger = logging.getLogger(__name__)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Décorateurs
    def teacher_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != 'teacher':
                flash('Accès non autorisé. Vous devez être un enseignant.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    
    # Routes
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        return render_template('index.html')

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
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                flash('Email ou mot de passe incorrect.', 'danger')
        return render_template('login.html', title='Connexion', form=form)

    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('index'))

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

    @app.route('/teacher_dashboard')
    @login_required
    @teacher_required
    def teacher_dashboard():
        teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
        return render_template('teacher_dashboard.html', classes=teacher_classes)

    @app.route('/student_dashboard')
    @login_required
    def student_dashboard():
        if current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        student_classes = current_user.enrolled_classes
        return render_template('student_dashboard.html', classes=student_classes)

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
            db.session.add(new_class)
            db.session.commit()
            flash('Classe créée avec succès!', 'success')
            return redirect(url_for('teacher_dashboard'))
        return render_template('create_class.html', title='Créer une classe', form=form)

    @app.route('/join_class', methods=['GET', 'POST'])
    @login_required
    def join_class():
        if current_user.role == 'teacher':
            flash('Les enseignants ne peuvent pas rejoindre une classe.', 'warning')
            return redirect(url_for('teacher_dashboard'))
        
        form = JoinClassForm()
        if form.validate_on_submit():
            class_code = form.class_code.data
            class_to_join = Class.query.filter_by(id=class_code).first()
            
            if not class_to_join:
                flash('Code de classe invalide.', 'danger')
                return redirect(url_for('join_class'))
            
            if class_to_join in current_user.enrolled_classes:
                flash('Vous êtes déjà inscrit à cette classe.', 'warning')
                return redirect(url_for('student_dashboard'))
            
            enrollment = ClassEnrollment(student_id=current_user.id, class_id=class_to_join.id)
            db.session.add(enrollment)
            db.session.commit()
            
            flash(f'Vous avez rejoint la classe {class_to_join.name} avec succès!', 'success')
            return redirect(url_for('student_dashboard'))
        
        return render_template('join_class.html', title='Rejoindre une classe', form=form)

    @app.route('/class/<int:class_id>/create_course', methods=['GET', 'POST'])
    @login_required
    @teacher_required
    def create_course(class_id):
        class_obj = Class.query.get_or_404(class_id)
        if class_obj.teacher_id != current_user.id:
            flash('Vous n\'avez pas la permission de créer un cours dans cette classe.', 'danger')
            return redirect(url_for('teacher_dashboard'))
        
        form = CourseForm()
        if form.validate_on_submit():
            new_course = Course(
                title=form.title.data,
                description=form.description.data,
                class_id=class_id
            )
            db.session.add(new_course)
            db.session.commit()
            flash('Cours créé avec succès!', 'success')
            return redirect(url_for('view_class', class_id=class_id))
        return render_template('create_course.html', title='Créer un cours', form=form, class_obj=class_obj)

    @app.route('/course/<int:course_id>/create_exercise', methods=['GET', 'POST'])
    @login_required
    @teacher_required
    def create_exercise(course_id):
        course = Course.query.get_or_404(course_id)
        if course.class_.teacher_id != current_user.id:
            flash('Vous n\'avez pas la permission de créer un exercice dans ce cours.', 'danger')
            return redirect(url_for('teacher_dashboard'))
        
        form = ExerciseForm()
        if form.validate_on_submit():
            new_exercise = Exercise(
                title=form.title.data,
                description=form.description.data,
                subject=form.subject.data,
                level=form.level.data,
                type=form.type.data,
                points=form.points.data,
                course_id=course_id
            )
            db.session.add(new_exercise)
            db.session.commit()
            flash('Exercice créé avec succès!', 'success')
            return redirect(url_for('view_course', course_id=course_id))
        return render_template('create_exercise.html', title='Créer un exercice', form=form, course=course)

    @app.route('/class/<int:class_id>')
    @login_required
    def view_class(class_id):
        class_obj = Class.query.get_or_404(class_id)
        if not current_user.role == 'teacher' and class_obj not in current_user.enrolled_classes:
            flash('Vous n\'avez pas accès à cette classe.', 'danger')
            return redirect(url_for('student_dashboard'))
        return render_template('view_class.html', class_obj=class_obj)

    @app.route('/course/<int:course_id>')
    @login_required
    def view_course(course_id):
        course = Course.query.get_or_404(course_id)
        if not current_user.role == 'teacher' and course.class_ not in current_user.enrolled_classes:
            flash('Vous n\'avez pas accès à ce cours.', 'danger')
            return redirect(url_for('student_dashboard'))
        return render_template('view_course.html', course=course)

    @app.route('/exercises/<int:exercise_id>')
    @login_required
    def view_exercise(exercise_id):
        try:
            logger.info(f"Tentative d'accès à l'exercice {exercise_id} par {current_user.username}")
            
            # Charger l'exercice avec toutes les relations nécessaires
            exercise = Exercise.query.options(
                db.joinedload(Exercise.course).joinedload(Course.class_),
                db.joinedload(Exercise.questions).joinedload(Question.choices),
                db.joinedload(Exercise.text_holes),
                db.joinedload(Exercise.pair_matches)
            ).get_or_404(exercise_id)
            
            logger.info(f"Exercice trouvé: {exercise.title} (Type: {exercise.exercise_type})")
            
            # Vérifier si l'utilisateur est l'enseignant qui a créé l'exercice
            is_creator = current_user.id == exercise.created_by
            logger.info(f"L'utilisateur est le créateur: {is_creator}")
            
            # Si c'est un enseignant qui n'a pas créé l'exercice
            if current_user.role == 'teacher' and not is_creator:
                logger.warning(f"Tentative d'accès non autorisé à l'exercice {exercise_id} par l'enseignant {current_user.username}")
                flash("Vous ne pouvez pas accéder à cet exercice car vous ne l'avez pas créé.", "error")
                return redirect(url_for('teacher_dashboard'))
            
            # Si c'est un étudiant, vérifier qu'il est inscrit dans la classe
            if current_user.role == 'student':
                logger.info("Vérification de l'inscription de l'étudiant")
                if exercise.course and exercise.course.class_:
                    class_enrollment = ClassEnrollment.query.filter_by(
                        student_id=current_user.id,
                        class_id=exercise.course.class_.id
                    ).first()
                    
                    if not class_enrollment:
                        logger.warning(f"L'étudiant {current_user.username} n'est pas inscrit dans la classe de l'exercice {exercise_id}")
                        flash("Vous devez être inscrit dans la classe pour accéder à cet exercice.", "error")
                        return redirect(url_for('student_dashboard'))
                else:
                    logger.info("L'exercice n'est pas associé à un cours")
                    flash("Cet exercice n'est pas disponible car il n'est pas associé à un cours.", "error")
                    return redirect(url_for('student_dashboard'))
            
            # Vérifier si l'étudiant a déjà soumis cet exercice
            submission = None
            if current_user.role == 'student':
                submission = ExerciseSubmission.query.filter_by(
                    student_id=current_user.id,
                    exercise_id=exercise_id
                ).first()
                logger.info(f"Soumission existante trouvée: {submission is not None}")
            
            logger.info("Rendu du template exercise.html")
            return render_template('exercise.html',
                                 exercise=exercise,
                                 is_creator=is_creator,
                                 submission=submission)
                                 
        except Exception as e:
            logger.error(f"Erreur lors de l'accès à l'exercice {exercise_id}: {str(e)}")
            logger.exception("Détails de l'erreur:")
            flash("Une erreur s'est produite lors de l'accès à l'exercice.", "error")
            return redirect(url_for('student_dashboard' if current_user.role == 'student' else 'teacher_dashboard'))

    @app.route('/exercises/<int:exercise_id>/submit', methods=['POST'])
    @login_required
    def submit_exercise(exercise_id):
        try:
            if current_user.is_teacher:
                flash("Les enseignants ne peuvent pas soumettre d'exercices.", "error")
                return redirect(url_for('view_exercise', exercise_id=exercise_id))
                
            # Récupérer l'exercice
            exercise = Exercise.query.get_or_404(exercise_id)
            
            # Vérifier si l'exercice appartient à un cours
            if not exercise.course:
                flash("Cet exercice n'est pas associé à un cours.", "error")
                return redirect(url_for('view_exercise', exercise_id=exercise_id))
                
            # Vérifier si l'étudiant est inscrit à la classe
            class_enrollment = ClassEnrollment.query.filter_by(
                student_id=current_user.id,
                class_id=exercise.course.class_.id
            ).first()
            
            if not class_enrollment:
                flash("Vous n'êtes pas inscrit à cette classe.", "error")
                return redirect(url_for('view_exercise', exercise_id=exercise_id))
            
            # Vérifier si l'exercice a déjà été soumis
            existing_submission = ExerciseSubmission.query.filter_by(
                student_id=current_user.id,
                exercise_id=exercise_id
            ).first()
            
            if existing_submission:
                flash("Vous avez déjà soumis cet exercice.", "warning")
                return redirect(url_for('view_exercise', exercise_id=exercise_id))
            
            # Traiter la soumission selon le type d'exercice
            score = 0
            answers = {}
            
            if exercise.exercise_type == 'QCM':
                total_questions = len(exercise.questions)
                correct_answers = 0
                
                if total_questions == 0:
                    flash("Cet exercice ne contient aucune question.", "error")
                    return redirect(url_for('view_exercise', exercise_id=exercise_id))
                
                for question in exercise.questions:
                    selected_choice_id = request.form.get(f'question_{question.id}')
                    if not selected_choice_id:
                        flash("Veuillez répondre à toutes les questions.", "error")
                        return redirect(url_for('view_exercise', exercise_id=exercise_id))
                    
                    answers[f'question_{question.id}'] = selected_choice_id
                    selected_choice = Choice.query.get(int(selected_choice_id))
                    if selected_choice and selected_choice.is_correct:
                        correct_answers += 1
                
                score = correct_answers / total_questions
                
            elif exercise.exercise_type == 'text_holes':
                total_holes = len(exercise.text_holes)
                correct_answers = 0
                
                if total_holes == 0:
                    flash("Cet exercice ne contient aucun trou à remplir.", "error")
                    return redirect(url_for('view_exercise', exercise_id=exercise_id))
                
                for hole in exercise.text_holes:
                    answer = request.form.get(f'hole_{hole.id}')
                    if not answer:
                        flash("Veuillez remplir tous les trous.", "error")
                        return redirect(url_for('view_exercise', exercise_id=exercise_id))
                    
                    answers[str(hole.id)] = answer
                    if answer.lower().strip() == hole.correct_answer.lower().strip():
                        correct_answers += 1
                
                score = correct_answers / total_holes
                
            elif exercise.exercise_type == 'pair_match':
                total_pairs = len(exercise.pair_matches)
                correct_pairs = 0
                
                if total_pairs == 0:
                    flash("Cet exercice ne contient aucune paire à associer.", "error")
                    return redirect(url_for('view_exercise', exercise_id=exercise_id))
                
                # Créer un dictionnaire des associations faites par l'étudiant
                student_pairs = {}
                for pair in exercise.pair_matches:
                    answer_key = f'pair_{pair.id}'
                    if answer_key not in request.form:
                        flash("Veuillez associer toutes les paires.", "error")
                        return redirect(url_for('view_exercise', exercise_id=exercise_id))
                        
                    selected_pair_id = request.form[answer_key]
                    student_pairs[str(pair.id)] = selected_pair_id
                    answers[str(pair.id)] = selected_pair_id
                
                # Vérifier les associations
                for pair_id, selected_id in student_pairs.items():
                    if pair_id == selected_id:
                        correct_pairs += 1
                
                score = correct_pairs / total_pairs
            
            else:
                flash("Type d'exercice non reconnu.", "error")
                return redirect(url_for('view_exercise', exercise_id=exercise_id))
            
            # Créer la soumission
            submission = ExerciseSubmission(
                student_id=current_user.id,
                exercise_id=exercise_id,
                score=score,
                answers=answers,
                submitted_at=datetime.utcnow()
            )
            
            db.session.add(submission)
            db.session.commit()
            
            # Message de réussite avec le score
            score_percentage = score * 100
            flash(f'Exercice soumis avec succès ! Score : {score_percentage:.1f}%', 'success')
            
            logger.info(f'Exercice {exercise_id} soumis par {current_user.id} avec un score de {score_percentage:.1f}%')
            
            return redirect(url_for('view_exercise', exercise_id=exercise_id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la soumission de l\'exercice {exercise_id}: {str(e)}')
            logger.exception("Détails de l'erreur:")
            flash('Une erreur est survenue lors de la soumission de l\'exercice.', 'error')
            return redirect(url_for('view_exercise', exercise_id=exercise_id))

    @app.route('/exercise_library')
    @login_required
    @teacher_required
    def exercise_library():
        exercises = Exercise.query.all()
        teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
        return render_template('exercise_library.html', exercises=exercises, teacher_classes=teacher_classes)

    @app.route('/api/filter_exercises')
    @login_required
    @teacher_required
    def filter_exercises():
        subject = request.args.get('subject')
        level = request.args.get('level')
        class_id = request.args.get('class_id')
        exercise_type = request.args.get('type')

        query = Exercise.query

        if subject:
            query = query.filter(Exercise.subject == subject)
        if level:
            query = query.filter(Exercise.level == level)
        if exercise_type:
            query = query.filter(Exercise.type == exercise_type)
        if class_id:
            query = query.join(Exercise.classes).filter(Class.id == class_id)

        exercises = query.all()
        return jsonify([{
            'id': ex.id,
            'title': ex.title,
            'description': ex.description,
            'subject': ex.subject,
            'level': ex.level,
            'type': ex.type,
            'points': ex.points,
            'created_at': ex.created_at.strftime('%Y-%m-%d %H:%M') if ex.created_at else None
        } for ex in exercises])

    @app.route('/exercise/<int:exercise_id>/add_to_class', methods=['POST'])
    @login_required
    @teacher_required
    def add_exercise_to_class(exercise_id):
        class_id = request.args.get('class_id')
        if not class_id:
            return jsonify({'error': 'Class ID is required'}), 400

        exercise = Exercise.query.get_or_404(exercise_id)
        class_obj = Class.query.get_or_404(class_id)

        if exercise in class_obj.exercises:
            return jsonify({'error': 'Exercise already added to this class'}), 400

        class_obj.exercises.append(exercise)
        db.session.commit()

        return jsonify({'message': 'Exercise added to class successfully'})

    @app.route('/exercise_stats')
    @login_required
    @teacher_required
    def exercise_stats():
        try:
            # Récupérer tous les exercices
            exercises = Exercise.query.all()
            
            # Statistiques globales
            total_exercises = len(exercises)
            total_submissions = ExerciseSubmission.query.count()
            all_scores = [sub.score for sub in ExerciseSubmission.query.all() if sub.score is not None]
            average_score = sum(all_scores) / len(all_scores) if all_scores else 0
            
            # Statistiques par exercice
            exercise_stats = []
            for exercise in exercises:
                submissions = ExerciseSubmission.query.filter_by(exercise_id=exercise.id).all()
                valid_submissions = [sub for sub in submissions if sub.score is not None]
                stats = {
                    'exercise_id': exercise.id,
                    'title': exercise.title,
                    'total_submissions': len(submissions),
                    'valid_submissions': len(valid_submissions),
                    'average_score': sum([sub.score for sub in valid_submissions]) / len(valid_submissions) if valid_submissions else 0
                }
                exercise_stats.append(stats)
            
            return render_template('exercise_stats.html',
                                total_exercises=total_exercises,
                                total_submissions=total_submissions,
                                average_score=average_score,
                                exercise_stats=exercise_stats)
        
        except Exception as e:
            logger.error(f"Erreur lors du calcul des statistiques : {str(e)}")
            flash("Une erreur s'est produite lors du calcul des statistiques.", "danger")
            return redirect(url_for('index'))

    @app.route('/exercise/<int:exercise_id>/stats')
    @login_required
    @teacher_required
    def exercise_specific_stats(exercise_id):
        try:
            exercise = Exercise.query.get_or_404(exercise_id)
            submissions = ExerciseSubmission.query.filter_by(exercise_id=exercise_id).all()
            
            # Statistiques générales
            total_submissions = len(submissions)
            valid_submissions = [sub for sub in submissions if sub.score is not None]
            average_score = sum([sub.score for sub in valid_submissions]) / len(valid_submissions) if valid_submissions else 0
            
            # Détails des soumissions
            submission_details = []
            for submission in submissions:
                student = User.query.get(submission.student_id)
                details = {
                    'student_name': f"{student.first_name} {student.last_name}",
                    'score': submission.score,
                    'submitted_at': submission.submitted_at,
                    'answers': submission.answers
                }
                submission_details.append(details)
            
            return render_template('exercise_specific_stats.html',
                                exercise=exercise,
                                total_submissions=total_submissions,
                                valid_submissions=len(valid_submissions),
                                average_score=average_score,
                                submission_details=submission_details)
        
        except Exception as e:
            logger.error(f"Erreur lors du chargement des statistiques détaillées : {str(e)}")
            flash("Une erreur s'est produite lors du chargement des statistiques détaillées.", "danger")
            return redirect(url_for('exercise_stats'))

    @app.route('/exercise/<int:exercise_id>/submit', methods=['POST'])
    @login_required
    def submit_exercise(exercise_id):
        if current_user.role == 'teacher':
            flash('Les enseignants ne peuvent pas soumettre d\'exercices.', 'warning')
            return redirect(url_for('view_exercise', exercise_id=exercise_id))
        
        exercise = Exercise.query.get_or_404(exercise_id)
        if exercise.course.class_ not in current_user.enrolled_classes:
            flash('Vous n\'avez pas accès à cet exercice.', 'danger')
            return redirect(url_for('student_dashboard'))
        
        try:
            answers = request.get_json()
            if not answers:
                return jsonify({'error': 'Réponses manquantes'}), 400
            
            submission = ExerciseSubmission(
                student_id=current_user.id,
                exercise_id=exercise_id,
                answers=json.dumps(answers),
                submitted_at=datetime.now(timezone.utc)
            )
            db.session.add(submission)
            db.session.commit()
            
            return jsonify({'message': 'Exercice soumis avec succès!'})
        except Exception as e:
            logger.error(f"Erreur lors de la soumission de l'exercice: {str(e)}")
            return jsonify({'error': 'Une erreur est survenue lors de la soumission'}), 500

    @app.route('/exercise/<int:exercise_id>/grade', methods=['POST'])
    @login_required
    @teacher_required
    def grade_exercise(exercise_id):
        exercise = Exercise.query.get_or_404(exercise_id)
        if exercise.course.class_.teacher_id != current_user.id:
            flash('Vous n\'avez pas la permission de noter cet exercice.', 'danger')
            return redirect(url_for('teacher_dashboard'))
        
        try:
            data = request.get_json()
            submission_id = data.get('submission_id')
            score = data.get('score')
            
            if not submission_id or score is None:
                return jsonify({'error': 'Données manquantes'}), 400
            
            submission = ExerciseSubmission.query.get_or_404(submission_id)
            if submission.exercise_id != exercise_id:
                return jsonify({'error': 'Soumission invalide'}), 400
            
            submission.score = score
            submission.graded_at = datetime.now(timezone.utc)
            db.session.commit()
            
            return jsonify({'message': 'Note attribuée avec succès!'})
        except Exception as e:
            logger.error(f"Erreur lors de la notation de l'exercice: {str(e)}")
            return jsonify({'error': 'Une erreur est survenue lors de la notation'}), 500

    return app

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Création des tables si elles n'existent pas
        db.create_all()
    app.run(debug=True)
