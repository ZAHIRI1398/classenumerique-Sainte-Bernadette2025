from app import app, db, Exercise, Question, Choice
import json

def check_exercise(exercise_id):
    with app.app_context():
        # Récupérer l'exercice avec ses relations
        exercise = Exercise.query.get(exercise_id)
        if not exercise:
            print(f"Exercice {exercise_id} non trouvé")
            return
        
        print("\nDétails de l'exercice:")
        print(f"ID: {exercise.id}")
        print(f"Titre: {exercise.title}")
        print(f"Type: {exercise.exercise_type}")
        print(f"Description: {exercise.description}")
        print(f"Contenu: {exercise.content}")
        print(f"Solution: {exercise.solution}")
        
        print("\nQuestions:")
        for question in exercise.questions:
            print(f"\n  Question ID: {question.id}")
            print(f"  Texte: {question.text}")
            print(f"  Image: {question.image}")
            
            print("  Choix:")
            for choice in question.choices:
                print(f"    - ID: {choice.id}")
                print(f"    - Texte: {choice.text}")
                print(f"    - Correct: {choice.is_correct}")

if __name__ == '__main__':
    check_exercise(1)  # Vérifier l'exercice avec ID 1
