from app import app, db
from models import Exercise

def update_exercise_types():
    with app.app_context():
        # Mettre à jour tous les exercices de type 'PAIR_MATCH' en 'pair_match'
        exercises = Exercise.query.filter_by(exercise_type='PAIR_MATCH').all()
        for exercise in exercises:
            exercise.exercise_type = 'pair_match'
        
        # Sauvegarder les changements
        db.session.commit()
        print(f"Mise à jour effectuée pour {len(exercises)} exercice(s)")

if __name__ == '__main__':
    update_exercise_types()
