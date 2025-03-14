from app import app, db
from models import User, Class, Course, Exercise, Question, Choice, TextHole

with app.app_context():
    # Supprimer toutes les tables existantes
    db.drop_all()
    
    # Créer toutes les tables
    db.create_all()
    
    print("Base de données créée avec succès!")
