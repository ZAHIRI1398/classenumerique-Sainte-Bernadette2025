from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, IntegerField, FloatField, FileField, HiddenField, MultipleFileField, BooleanField, FormField, FieldList
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange, Optional
from flask_wtf.file import FileAllowed
from flask import request
from models import User

class LoginForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    remember = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')

class RegistrationForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])
    user_type = SelectField('Type d\'utilisateur', choices=[
        ('student', 'Étudiant'),
        ('teacher', 'Enseignant')
    ], validators=[DataRequired()])
    submit = SubmitField('S\'inscrire')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Ce nom d\'utilisateur est déjà pris.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Cette adresse email est déjà utilisée.')

class ClassForm(FlaskForm):
    name = StringField('Nom de la classe', validators=[
        DataRequired(message="Le nom de la classe est requis"),
        Length(min=2, max=100, message="Le nom doit faire entre 2 et 100 caractères")
    ])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Créer la classe')

class CourseForm(FlaskForm):
    title = StringField('Titre du cours', validators=[DataRequired()])
    description = TextAreaField('Description')
    content = TextAreaField('Contenu du cours')
    files = MultipleFileField('Ajouter des fichiers')
    submit = SubmitField('Créer le cours')

class ChoiceForm(FlaskForm):
    class Meta:
        csrf = False
    text = StringField('Réponse', validators=[Optional()])
    is_correct = BooleanField('Correcte')

class QuestionForm(FlaskForm):
    class Meta:
        csrf = False
    text = StringField('Question', validators=[Optional()])
    choices = FieldList(FormField(ChoiceForm), min_entries=4)

class TextHoleForm(FlaskForm):
    class Meta:
        csrf = False
    text_before = TextAreaField('Texte avant le trou', validators=[Optional()])
    correct_answer = StringField('Mot à placer', validators=[Optional()])
    text_after = TextAreaField('Texte après le trou', validators=[Optional()])

class PairMatchForm(FlaskForm):
    class Meta:
        csrf = False
    left_type = SelectField('Type gauche', choices=[('text', 'Texte'), ('image', 'Image')], validators=[DataRequired()])
    right_type = SelectField('Type droite', choices=[('text', 'Texte'), ('image', 'Image')], validators=[DataRequired()])
    left_content = StringField('Contenu gauche', validators=[Optional()])
    right_content = StringField('Contenu droite', validators=[Optional()])
    left_image = FileField('Image gauche', validators=[Optional(), FileAllowed(['jpg', 'png', 'gif'], 'Images uniquement!')])
    right_image = FileField('Image droite', validators=[Optional(), FileAllowed(['jpg', 'png', 'gif'], 'Images uniquement!')])

class ExerciseForm(FlaskForm):
    title = StringField('Titre', validators=[DataRequired()])
    description = TextAreaField('Description')
    subject = SelectField('Matière', choices=[
        ('mathematiques_nombres', 'Mathématiques - Nombres et opérations'),
        ('mathematiques_grandeurs', 'Mathématiques - Grandeurs'),
        ('mathematiques_solides', 'Mathématiques - Solides et Figures'),
        ('francais_grammaire', 'Français - Grammaire'),
        ('francais_conjugaison', 'Français - Conjugaison'),
        ('francais_vocabulaire', 'Français - Vocabulaire'),
        ('francais_dictee', 'Français - Dictée'),
        ('eveil_histoire', 'Eveil - Histoire'),
        ('eveil_geographie', 'Eveil - Géographie'),
        ('sciences_biologie', 'Sciences - Biologie'),
        ('sciences_physique', 'Sciences - Physique')
    ], validators=[DataRequired()])
    level = SelectField('Niveau', choices=[
        ('1obs', '1obs'),
        ('1phase', '1phase'),
        ('2phase', '2phase'),
        ('6ème', '6ème'),
        ('5ème', '5ème'),
        ('4ème', '4ème'),
        ('3ème', '3ème'),
        ('2nde', '2nde'),
        ('1ère', '1ère'),
        ('terminale', 'Terminale')
    ], validators=[DataRequired()])
    difficulty = SelectField('Difficulté', choices=[
        ('easy', 'Facile'),
        ('medium', 'Moyen'),
        ('hard', 'Difficile')
    ], validators=[DataRequired()])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=1)])
    exercise_type = SelectField('Type d\'exercice', choices=[
        ('QCM', 'Questions à choix multiples'),
        ('text_holes', 'Texte à trous'),
        ('PAIR_MATCH', 'Association de paires')
    ], validators=[DataRequired()])
    course_id = SelectField('Cours', coerce=int, validators=[DataRequired()])
    image = FileField('Image', validators=[Optional(), FileAllowed(['jpg', 'png', 'gif'], 'Images uniquement!')])
    
    # Fields for QCM
    questions = FieldList(FormField(QuestionForm), min_entries=1)
    
    # Fields for text holes
    text_holes = FieldList(FormField(TextHoleForm), min_entries=1)
    
    # Fields for pair matches
    pair_matches = FieldList(FormField(PairMatchForm), min_entries=1)
    
    submit = SubmitField('Créer l\'exercice')

class JoinClassForm(FlaskForm):
    code = StringField('Code d\'invitation', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Rejoindre la classe')

class GradeForm(FlaskForm):
    score = FloatField('Note (en %)', validators=[
        DataRequired(message="La note est requise"),
        NumberRange(min=0, max=100, message="La note doit être comprise entre 0 et 100")
    ])
    feedback = TextAreaField('Commentaire')
    submit = SubmitField('Enregistrer la note')
