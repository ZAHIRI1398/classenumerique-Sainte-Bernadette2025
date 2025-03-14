from flask import render_template, url_for, flash, redirect, request, jsonify, send_from_directory
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.utils import secure_filename
import os
import json
from app import app, db, bcrypt
from forms import (LoginForm, RegistrationForm, ClassForm, CourseForm, 
                  ExerciseForm, JoinClassForm, GradeForm)
from models import (User, Class, Course, Exercise, Question, Choice, 
                   TextHole, ExerciseSubmission, UserClass)

@app.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return render_template('index.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, 
                   email=form.email.data,
                   password=hashed_password,
                   role=form.role.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Votre compte a été créé avec succès!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Inscription', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Connexion échouée. Vérifiez votre email et mot de passe.', 'danger')
    return render_template('login.html', title='Connexion', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/class/create", methods=['GET', 'POST'])
@login_required
def create_class():
    if current_user.role != 'teacher':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('index'))
    
    form = ClassForm()
    if form.validate_on_submit():
        new_class = Class(name=form.name.data,
                         description=form.description.data,
                         teacher_id=current_user.id)
        db.session.add(new_class)
        db.session.commit()
        flash(f'La classe {form.name.data} a été créée avec succès!', 'success')
        return redirect(url_for('teacher_dashboard'))
    return render_template('create_class.html', title='Créer une classe', form=form)

@app.route("/course/<int:course_id>/exercises/create", methods=['GET', 'POST'])
@login_required
def create_exercise(course_id):
    if current_user.role != 'teacher':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('index'))
    
    course = Course.query.get_or_404(course_id)
    if course.class_.teacher_id != current_user.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('index'))
    
    form = ExerciseForm()
    
    if request.method == 'POST':
        try:
            if form.validate():
                # Récupérer les données du formulaire
                exercise_data = {
                    'title': form.title.data,
                    'description': form.description.data,
                    'difficulty': form.difficulty.data,
                    'points': form.points.data,
                    'exercise_type': form.exercise_type.data,
                    'content': {}
                }
                
                # Traiter les données spécifiques au type d'exercice
                if form.exercise_type.data == 'qcm':
                    questions = []
                    for i, q_text in enumerate(request.form.getlist('questions[][text]')):
                        question = {
                            'text': q_text,
                            'choices': []
                        }
                        
                        choices = []
                        choice_texts = request.form.getlist(f'questions[{i}][choices][][text]')
                        correct_choice = request.form.get(f'questions[{i}][correct]')
                        
                        for j, text in enumerate(choice_texts):
                            choices.append({
                                'text': text,
                                'is_correct': str(j) == correct_choice
                            })
                        question['choices'] = choices
                        questions.append(question)
                    
                    exercise_data['content']['questions'] = questions
                    
                elif form.exercise_type.data == 'mots_a_placer':
                    exercise_data['content']['text_with_holes'] = request.form.get('text_with_holes')
                    
                elif form.exercise_type.data == 'vrai_faux':
                    statements = []
                    for i in range(len(request.form.getlist('statements[][text]'))):
                        statements.append({
                            'text': request.form.get(f'statements[{i}][text]'),
                            'correct': request.form.get(f'statements[{i}][correct]') == 'true'
                        })
                    exercise_data['content']['statements'] = statements
                    
                elif form.exercise_type.data == 'texte_libre':
                    exercise_data['content']['question'] = request.form.get('free_text_question')
                    exercise_data['content']['keywords'] = [
                        k.strip() for k in request.form.get('keywords', '').split(',')
                        if k.strip()
                    ]
                    
                elif form.exercise_type.data == 'correspondance':
                    pairs = []
                    for i in range(len(request.form.getlist('pairs[][left]'))):
                        pairs.append({
                            'left': request.form.get(f'pairs[{i}][left]'),
                            'right': request.form.get(f'pairs[{i}][right]')
                        })
                    exercise_data['content']['pairs'] = pairs
                    
                elif form.exercise_type.data == 'ordre':
                    exercise_data['content']['items'] = request.form.getlist('order_items[]')
                    
                elif form.exercise_type.data == 'calcul':
                    exercise_data['content']['expression'] = request.form.get('calculation_expression')
                    exercise_data['content']['solution'] = request.form.get('calculation_solution')
                    
                elif form.exercise_type.data == 'dessin':
                    exercise_data['content']['instructions'] = request.form.get('drawing_instructions')
                    points_str = request.form.get('validation_points', '')
                    points = [
                        tuple(map(float, p.strip().split(','))) 
                        for p in points_str.split(';') 
                        if p.strip()
                    ]
                    exercise_data['content']['validation_points'] = points

                # Créer l'exercice
                exercise = Exercise(
                    title=exercise_data['title'],
                    description=exercise_data['description'],
                    difficulty=exercise_data['difficulty'],
                    points=exercise_data['points'],
                    exercise_type=exercise_data['exercise_type'],
                    content=json.dumps(exercise_data['content']),
                    course_id=course_id
                )
                
                # Gérer l'image si elle est fournie
                if form.image.data:
                    try:
                        image = form.image.data
                        filename = secure_filename(image.filename)
                        image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'exercises', filename)
                        os.makedirs(os.path.dirname(image_path), exist_ok=True)
                        image.save(image_path)
                        exercise.image = filename
                    except Exception as e:
                        flash(f'Erreur lors du téléchargement de l\'image: {str(e)}', 'danger')
                        return render_template('create_exercise.html', title='Créer un exercice', 
                                            form=form, course=course)

                try:
                    db.session.add(exercise)
                    db.session.commit()
                    flash('L\'exercice a été créé avec succès!', 'success')
                    return redirect(url_for('view_course', course_id=course_id))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erreur lors de la création de l\'exercice: {str(e)}', 'danger')
                    return render_template('create_exercise.html', title='Créer un exercice', 
                                        form=form, course=course)
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f'Erreur dans le champ {field}: {error}', 'danger')
        except Exception as e:
            flash(f'Une erreur inattendue est survenue: {str(e)}', 'danger')
        
    return render_template('create_exercise.html', title='Créer un exercice', 
                         form=form, course=course)

@app.route("/exercises/<int:exercise_id>")
@login_required
def view_exercise(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    
    # Si l'exercice fait partie d'un cours, vérifier l'accès
    if exercise.course:
        if current_user.role != 'teacher' and current_user not in exercise.course.class_.students:
            flash('Accès non autorisé.', 'danger')
            return redirect(url_for('index'))
    
    # Vérifier si l'utilisateur est inscrit dans la classe
    is_enrolled = False
    if exercise.course and exercise.course.class_:
        is_enrolled = current_user in exercise.course.class_.students
    
    return render_template('view_exercise.html', 
                         exercise=exercise,
                         is_enrolled=is_enrolled)

@app.route("/exercises/<int:exercise_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_exercise(exercise_id):
    app.logger.info(f"Tentative de modification de l'exercice {exercise_id}")
    
    if not current_user.role == 'teacher':
        app.logger.warning(f"Accès refusé : l'utilisateur {current_user.id} n'est pas un enseignant")
        flash("Vous n'avez pas les droits pour modifier cet exercice.", "danger")
        return redirect(url_for('index'))
    
    exercise = Exercise.query.get_or_404(exercise_id)
    app.logger.info(f"Exercice trouvé : {exercise.title}")
    
    if exercise.teacher_id != current_user.id:
        app.logger.warning(f"Accès refusé : l'exercice appartient à l'enseignant {exercise.teacher_id}, pas à {current_user.id}")
        flash("Vous n'avez pas les droits pour modifier cet exercice.", "danger")
        return redirect(url_for('index'))
    
    form = ExerciseForm()
    app.logger.debug(f"Méthode de la requête : {request.method}")
    
    if request.method == 'GET':
        app.logger.info("Chargement du formulaire avec les données existantes")
        form.title.data = exercise.title
        form.description.data = exercise.description
        form.difficulty.data = exercise.difficulty
        form.points.data = exercise.points
        form.exercise_type.data = exercise.exercise_type
    
    if form.validate_on_submit():
        app.logger.info("Formulaire validé, mise à jour de l'exercice")
        try:
            exercise.title = form.title.data
            exercise.description = form.description.data
            exercise.difficulty = form.difficulty.data
            exercise.points = form.points.data
            exercise.exercise_type = form.exercise_type.data
            
            if form.image.data:
                app.logger.info("Nouvelle image détectée, traitement en cours")
                file = form.image.data
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    exercise.image_path = os.path.join('uploads', filename)
                    app.logger.info(f"Image sauvegardée : {exercise.image_path}")
            
            db.session.commit()
            app.logger.info("Modifications sauvegardées avec succès")
            flash('Exercice modifié avec succès!', 'success')
            return redirect(url_for('view_exercise', exercise_id=exercise.id))
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la mise à jour de l'exercice : {str(e)}")
            db.session.rollback()
            flash('Une erreur est survenue lors de la modification de l\'exercice.', 'danger')
    else:
        if form.errors:
            app.logger.warning(f"Erreurs de validation du formulaire : {form.errors}")
    
    app.logger.info("Affichage du formulaire d'édition")
    return render_template('edit_exercise.html', title='Modifier l\'exercice',
                         form=form, exercise=exercise)

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
        "teacher_id": exercise.teacher_id
    })

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
            "teacher_id": ex.teacher_id,
            "course_id": ex.course_id
        })
    return jsonify(result)
