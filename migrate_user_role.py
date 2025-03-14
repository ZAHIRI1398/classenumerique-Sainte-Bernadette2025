from app import app, db
from models import User
import sqlite3

def migrate_user_role():
    # Connexion directe à la base de données SQLite
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    
    try:
        # Ajouter la nouvelle colonne role
        cursor.execute('''
        ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'student'
        ''')
        
        # Mettre à jour les rôles en fonction de is_teacher
        cursor.execute('''
        UPDATE user SET role = 'teacher' WHERE is_teacher = 1
        ''')
        
        # Supprimer l'ancienne colonne is_teacher
        cursor.execute('''
        CREATE TABLE user_new (
            id INTEGER PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(128),
            role VARCHAR(20) NOT NULL DEFAULT 'student'
        )
        ''')
        
        cursor.execute('''
        INSERT INTO user_new (id, username, email, password_hash, role)
        SELECT id, username, email, password_hash, role FROM user
        ''')
        
        cursor.execute('DROP TABLE user')
        cursor.execute('ALTER TABLE user_new RENAME TO user')
        
        conn.commit()
        print("Migration réussie!")
        
    except Exception as e:
        conn.rollback()
        print(f"Erreur lors de la migration : {str(e)}")
        
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_user_role()
