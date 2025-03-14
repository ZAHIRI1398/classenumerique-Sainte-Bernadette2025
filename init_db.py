from app import app, db
from models import User, Class, Course, Exercise, Question, Choice, TextHole, ExerciseSubmission
from werkzeug.security import generate_password_hash

def init_db():
    with app.app_context():
        # Créer toutes les tables
        db.drop_all()  # Supprimer toutes les tables existantes
        db.create_all()  # Créer toutes les tables
        
        # Créer un utilisateur admin par défaut
        admin = User(
            username='admin',
            email='admin@example.com',
            role='teacher'
        )
        admin.set_password('admin')
        
        # Ajouter l'admin à la base de données
        db.session.add(admin)
        db.session.commit()
        
        print("Base de données initialisée avec succès!")
        print("Compte admin créé:")
        print("Username: admin")
        print("Password: admin")

if __name__ == '__main__':
    init_db()
