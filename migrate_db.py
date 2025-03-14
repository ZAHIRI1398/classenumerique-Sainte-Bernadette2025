from extensions import db
from flask import Flask
from models import User, Class, Course, Exercise, ExerciseSubmission
import sqlite3
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def migrate_database():
    with app.app_context():
        # Création des tables
        db.create_all()
        print("Base de données migrée avec succès!")

def migrate_database_sqlite(db_path):
    print(f"\nMigration de la base de données: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Créer une table temporaire
        c.execute('''
            CREATE TABLE exercise_new (
                id INTEGER PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                exercise_type VARCHAR(50) NOT NULL,
                content TEXT,
                solution TEXT,
                difficulty VARCHAR(20),
                points INTEGER,
                subject VARCHAR(100),
                level VARCHAR(50),
                image_path VARCHAR(255),
                is_in_library BOOLEAN DEFAULT 0,
                created_at DATETIME,
                course_id INTEGER,
                created_by INTEGER NOT NULL,
                FOREIGN KEY (course_id) REFERENCES course (id),
                FOREIGN KEY (created_by) REFERENCES user (id)
            )
        ''')
        
        # Copier les données
        c.execute('''
            INSERT INTO exercise_new 
            SELECT * FROM exercise
        ''')
        
        # Supprimer l'ancienne table
        c.execute('DROP TABLE exercise')
        
        # Renommer la nouvelle table
        c.execute('ALTER TABLE exercise_new RENAME TO exercise')
        
        conn.commit()
        print(f"Migration réussie pour {db_path}")
        
    except sqlite3.Error as e:
        print(f"Erreur lors de la migration de {db_path}: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()
    db_files = ['classe_numerique.db', 'site.db']
    for db_file in db_files:
        db_path = os.path.join('instance', db_file)
        if os.path.exists(db_path):
            migrate_database_sqlite(db_path)
