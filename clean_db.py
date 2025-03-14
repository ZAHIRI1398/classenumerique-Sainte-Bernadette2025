from app import app, db
import sqlite3
import shutil
import os
from models import Exercise

# Supprimer le dossier migrations s'il existe
if os.path.exists('migrations'):
    shutil.rmtree('migrations')

# Supprimer la base de données si elle existe
if os.path.exists('instance/site.db'):
    os.remove('instance/site.db')

# Créer le dossier instance s'il n'existe pas
os.makedirs('instance', exist_ok=True)

# Recréer les tables
with app.app_context():
    db.create_all()

# Supprimer tous les exercices sans course_id
with app.app_context():
    Exercise.query.filter_by(course_id=None).delete()
    db.session.commit()
