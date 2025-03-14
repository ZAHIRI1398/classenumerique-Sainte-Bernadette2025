import sqlite3
import os

def fix_course_id(db_path):
    print(f"\nCorrection de la base de données: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Créer une table temporaire sans la contrainte NOT NULL sur course_id
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
        print(f"Correction réussie pour {db_path}")
        
    except sqlite3.Error as e:
        print(f"Erreur lors de la correction de {db_path}: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    # Utiliser uniquement la base de données de la version originale
    db_path = os.path.join('instance', 'classe_numerique.db')
    if os.path.exists(db_path):
        fix_course_id(db_path)
