import os
import sys
import logging
from datetime import datetime
from app import app, db, Exercise, Question, Choice, TextHole, PairMatch, User

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_database():
    logger.info("Application démarrée\n")
    
    # Afficher le chemin de la base de données
    db_path = os.path.join('instance', 'classe_numerique.db')
    print(f"\nDébogage de la base de données: {db_path}\n")
    
    # Récupérer tous les exercices
    exercises = Exercise.query.all()
    
    print("\nDétails des exercices:\n")
    
    for exercise in exercises:
        print(f"Exercice ID: {exercise.id}")
        print(f"Titre: {exercise.title}")
        print(f"Description: {exercise.description}")
        print(f"Type: {exercise.exercise_type}")
        print(f"Contenu: {exercise.content}")
        print(f"Solution: {exercise.solution}")
        print(f"Difficulté: {exercise.difficulty}")
        print(f"Points: {exercise.points}")
        print(f"Matière: {exercise.subject}")
        print(f"Niveau: {exercise.level}")
        print(f"Course ID: {exercise.course_id}")
        
        # Récupérer le créateur
        creator = User.query.get(exercise.created_by)
        print(f"Créé par: {exercise.created_by} ({creator.username if creator else 'Inconnu'})")
        
        if exercise.exercise_type == 'QCM':
            print("\nQuestions:")
            for question in exercise.questions:
                print(f"\n  Question ID: {question.id}")
                print(f"  Texte: {question.text}")
                print(f"  Image: {question.image}")
                print("  Choix:")
                for choice in question.choices:
                    print(f"    - ID: {choice.id}, Texte: {choice.text}, Correct: {choice.is_correct}")
        
        elif exercise.exercise_type == 'text_holes':
            print("\nTrous de texte:\n")
            for hole in exercise.text_holes:
                print(f"  Trou ID: {hole.id}")
                print(f"  Texte avant: {hole.text_before}")
                print(f"  Réponse correcte: {hole.correct_answer}")
                print(f"  Texte après: {hole.text_after}")
                print()
        
        elif exercise.exercise_type == 'pair_match':
            print("\nPaires d'association:\n")
            for pair in exercise.pair_matches:
                print(f"  Paire ID: {pair.id}")
                print(f"  Type gauche: {pair.left_type}")
                print(f"  Contenu gauche: {pair.left_content}")
                print(f"  Type droit: {pair.right_type}")
                print(f"  Contenu droit: {pair.right_content}")
                print(f"  Position: {pair.position}")
                print()
        
        print("\n")

if __name__ == '__main__':
    with app.app_context():
        debug_database()
