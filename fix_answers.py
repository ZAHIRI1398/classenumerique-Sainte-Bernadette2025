from app import app, db, Choice, Question

def fix_correct_answers():
    with app.app_context():
        # Trouver la question sur la somme des angles
        question = Question.query.filter_by(id=1).first()
        if question:
            print(f"Question trouvée: {question.text}")
            
            # Trouver le choix avec 180°
            correct_choice = None
            for choice in question.choices:
                print(f"Vérifiant choix: {choice.text}")
                if "180" in choice.text:
                    correct_choice = choice
                    break
            
            if correct_choice:
                print(f"Marquage de '{correct_choice.text}' comme la bonne réponse")
                # Marquer toutes les réponses comme incorrectes d'abord
                for choice in question.choices:
                    choice.is_correct = False
                # Puis marquer la bonne réponse
                correct_choice.is_correct = True
                db.session.commit()
                print("Base de données mise à jour avec succès!")
            else:
                print("Choix '180°' non trouvé!")
        else:
            print("Question non trouvée!")

if __name__ == '__main__':
    fix_correct_answers()
