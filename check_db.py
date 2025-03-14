import sqlite3
import os

def check_database(db_path):
    print(f"\nVérification de la base de données: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Liste des tables à vérifier
        tables = ['exercise', 'course', 'class', 'user', 'question', 'choice', 'text_hole', 'exercise_submission']
        
        for table in tables:
            print(f"\nStructure de la table '{table}':")
            try:
                c.execute(f"PRAGMA table_info({table})")
                columns = c.fetchall()
                if columns:
                    for column in columns:
                        print(f"- {column[1]} ({column[2]}) {'NOT NULL' if column[3] else 'NULL'}")
                else:
                    print("Table non trouvée")
            except sqlite3.Error as e:
                print(f"Erreur lors de la vérification de la table {table}: {e}")
        
        # Vérifier les exercices sans cours
        print("\nExercices sans cours:")
        try:
            c.execute("SELECT id, title FROM exercise WHERE course_id IS NULL")
            exercises = c.fetchall()
            if exercises:
                for ex in exercises:
                    print(f"- ID: {ex[0]}, Titre: {ex[1]}")
            else:
                print("Aucun exercice sans cours trouvé")
        except sqlite3.Error as e:
            print(f"Erreur lors de la vérification des exercices sans cours: {e}")
        
        conn.close()
    except sqlite3.Error as e:
        print(f"Erreur lors de la connexion à la base de données: {e}")

if __name__ == '__main__':
    db_files = [f for f in os.listdir('instance') if f.endswith('.db')]
    for db_file in db_files:
        db_path = os.path.join('instance', db_file)
        if os.path.exists(db_path):
            check_database(db_path)
