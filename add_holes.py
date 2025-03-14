from app import app, db
from models import Exercise, TextHole

def add_holes_to_exercise():
    with app.app_context():
        # Récupérer l'exercice avec ID 2
        exercise = Exercise.query.get(2)
        
        if not exercise:
            print("Exercice non trouvé!")
            return
            
        # Supprimer les trous existants
        for hole in exercise.text_holes:
            db.session.delete(hole)
        db.session.commit()
        
        # Créer de nouveaux trous
        holes = [
            TextHole(
                text_before="La moitié de 100 est ",
                correct_answer="50",
                text_after=".",
                exercise=exercise
            ),
            TextHole(
                text_before="Le quart de 100 est ",
                correct_answer="25",
                text_after=".",
                exercise=exercise
            )
        ]
        
        # Ajouter les trous à la base de données
        for hole in holes:
            db.session.add(hole)
        
        # Sauvegarder les changements
        db.session.commit()
        print("Trous ajoutés avec succès!")

if __name__ == '__main__':
    add_holes_to_exercise()
