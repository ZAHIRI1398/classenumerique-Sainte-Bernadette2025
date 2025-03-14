from app import app, db
from models import User, Class, Course, Exercise, Question, Choice
from datetime import datetime, timedelta

def create_test_data():
    with app.app_context():
        # Supprimer toutes les données existantes
        db.session.query(Choice).delete()
        db.session.query(Question).delete()
        db.session.query(Exercise).delete()
        db.session.query(Course).delete()
        db.session.query(Class).delete()
        db.session.query(User).delete()
        db.session.commit()

        # Créer un professeur
        teacher = User(
            username='prof1',
            email='prof1@example.com',
            role='teacher'
        )
        teacher.set_password('password123')
        db.session.add(teacher)
        db.session.commit()

        # Créer une classe
        class1 = Class(
            name='Mathématiques 6ème A',
            description='Classe de mathématiques pour les 6ème A',
            teacher=teacher
        )
        db.session.add(class1)
        db.session.commit()

        # Créer un cours
        course = Course(
            title='Géométrie',
            description='Introduction à la géométrie',
            class_ref=class1
        )
        db.session.add(course)
        db.session.commit()

        # Créer un exercice QCM
        exercise = Exercise(
            title='Les formes géométriques',
            description='Identifier les différentes formes géométriques',
            course=course,
            exercise_type='qcm',
            image_path='geometric_shapes.jpg',
            due_date=datetime.utcnow() + timedelta(days=7)
        )
        db.session.add(exercise)
        db.session.commit()

        # Créer des questions pour le QCM
        question1 = Question(
            text='Quelle est la forme qui a 3 côtés égaux ?',
            exercise=exercise
        )
        db.session.add(question1)

        # Ajouter les choix pour la question 1
        choices1 = [
            Choice(text='Triangle équilatéral', is_correct=True, question=question1),
            Choice(text='Carré', is_correct=False, question=question1),
            Choice(text='Rectangle', is_correct=False, question=question1),
            Choice(text='Cercle', is_correct=False, question=question1)
        ]
        db.session.add_all(choices1)

        question2 = Question(
            text='Combien de côtés a un carré ?',
            exercise=exercise
        )
        db.session.add(question2)

        # Ajouter les choix pour la question 2
        choices2 = [
            Choice(text='3', is_correct=False, question=question2),
            Choice(text='4', is_correct=True, question=question2),
            Choice(text='5', is_correct=False, question=question2),
            Choice(text='6', is_correct=False, question=question2)
        ]
        db.session.add_all(choices2)

        # Créer quelques étudiants
        students = []
        for i in range(3):
            student = User(
                username=f'student{i+1}',
                email=f'student{i+1}@example.com',
                role='student'
            )
            student.set_password('password123')
            students.append(student)
        
        db.session.add_all(students)
        db.session.commit()

        # Ajouter les étudiants à la classe
        for student in students:
            class1.students.append(student)
        
        db.session.commit()

        print("Données de test créées avec succès!")
        print(f"Professeur créé: {teacher.username}")
        print(f"Classe créée: {class1.name}")
        print(f"Cours créé: {course.title}")
        print(f"Exercice créé: {exercise.title}")
        print("Étudiants créés:", ", ".join(s.username for s in students))

if __name__ == '__main__':
    create_test_data()
