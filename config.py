import os
from datetime import timedelta

# Configuration de base
SECRET_KEY = '5791628bb0b13ce0c676dfde280ba245'
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'classe_numerique.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Configuration des sessions et cookies
PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # Sessions durent 7 jours
REMEMBER_COOKIE_DURATION = timedelta(days=7)    # Cookie "remember me" dure 7 jours
REMEMBER_COOKIE_SECURE = False  # Mettre à True en production
REMEMBER_COOKIE_HTTPONLY = True

# Configuration du dossier d'upload
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# S'assurer que le dossier d'upload existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
