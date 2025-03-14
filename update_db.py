from app import app, db
import sqlite3
import os

def update_database():
    db_path = os.path.join(app.instance_path, 'database.db')
    
    # Connexion directe à SQLite
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # Vérifier si la colonne existe déjà
        c.execute("PRAGMA table_info(class)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'invite_code' not in columns:
            # Ajouter la colonne invite_code
            c.execute("ALTER TABLE class ADD COLUMN invite_code VARCHAR(6)")
            print("Colonne invite_code ajoutée avec succès!")
        else:
            print("La colonne invite_code existe déjà")
        
        conn.commit()
    except Exception as e:
        print(f"Erreur: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    with app.app_context():
        update_database()
