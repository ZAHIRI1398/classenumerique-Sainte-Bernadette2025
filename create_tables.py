import sqlite3
import os

def create_database():
    # Supprimer la base de données existante
    db_path = 'instance/database.db'
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Créer le dossier instance si nécessaire
    if not os.path.exists('instance'):
        os.makedirs('instance')
    
    # Créer une nouvelle connexion
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Créer la table user
    c.execute('''
        CREATE TABLE user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(80) NOT NULL UNIQUE,
            email VARCHAR(120) NOT NULL UNIQUE,
            password_hash VARCHAR(128),
            is_teacher BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Créer la table class avec le champ invite_code
    c.execute('''
        CREATE TABLE class (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            teacher_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            invite_code VARCHAR(6),
            FOREIGN KEY (teacher_id) REFERENCES user (id)
        )
    ''')
    
    # Créer la table class_enrollments
    c.execute('''
        CREATE TABLE class_enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES user (id),
            FOREIGN KEY (class_id) REFERENCES class (id)
        )
    ''')
    
    # Créer la table course
    c.execute('''
        CREATE TABLE course (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(100) NOT NULL,
            description TEXT,
            content TEXT,
            class_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (class_id) REFERENCES class (id)
        )
    ''')
    
    # Créer la table exercise
    c.execute('''
        CREATE TABLE exercise (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            is_in_library BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            course_id INTEGER,
            created_by INTEGER NOT NULL,
            FOREIGN KEY (course_id) REFERENCES course (id),
            FOREIGN KEY (created_by) REFERENCES user (id)
        )
    ''')
    
    # Créer la table class_exercises
    c.execute('''
        CREATE TABLE class_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (class_id) REFERENCES class (id),
            FOREIGN KEY (exercise_id) REFERENCES exercise (id)
        )
    ''')
    
    # Sauvegarder les changements et fermer la connexion
    conn.commit()
    conn.close()
    
    print("Base de données créée avec succès!")

if __name__ == '__main__':
    create_database()
