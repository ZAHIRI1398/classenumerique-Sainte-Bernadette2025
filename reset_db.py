from app import app, db
import os

def reset_database():
    # Supprimer la base de données existante
    db_path = os.path.join(app.instance_path, 'database.db')
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Base de données supprimée : {db_path}")
    
    # Créer le dossier instance si nécessaire
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)
    
    # Créer une nouvelle base de données avec les tables
    with app.app_context():
        print("Suppression de toutes les tables...")
        db.drop_all()
        print("Création des nouvelles tables...")
        db.create_all()
        print("Base de données réinitialisée avec succès!")

if __name__ == '__main__':
    reset_database()
