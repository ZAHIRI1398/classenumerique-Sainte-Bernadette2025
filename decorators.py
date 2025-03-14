from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_teacher:
            flash('Accès réservé aux enseignants.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_teacher:
            flash('Accès réservé aux étudiants.', 'danger')
            return redirect(url_for('teacher_dashboard'))
        return f(*args, **kwargs)
    return decorated_function
