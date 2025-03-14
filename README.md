# Classe Numérique

Une plateforme éducative pour les enseignants et les élèves, permettant la création et la gestion d'exercices interactifs.

## Fonctionnalités

### Pour les enseignants
- Création et gestion de classes
- Création d'exercices personnalisés
- Suivi des progrès des élèves
- Attribution d'exercices aux classes

### Pour les élèves
- Accès aux exercices de leurs classes
- Réalisation des exercices en ligne
- Consultation de leurs résultats

### Bibliothèque d'exercices
- **Mathématiques**
  - Nombres et opérations
  - Solides et figures
  - Grandeurs
- **Français**
  - Grammaire
  - Conjugaison
  - Orthographe
  - Vocabulaire
  - Lecture/Écriture
  - Littérature
- **Autres matières**
  - Éveil
  - Sciences

### Types d'exercices
- QCM (Questions à choix multiples)
- Questions ouvertes
- Textes à trous

## Installation

1. Installer Python (version 3.8 ou supérieure)

2. Cloner le projet :
```bash
git clone https://github.com/votre-nom/classe-numerique.git
cd classe-numerique
```

3. Créer et activer l'environnement virtuel :
```bash
# Windows
python -m venv venv
venv\Scripts\activate
```

4. Installer les dépendances :
```bash
pip install -r requirements.txt
```

5. Initialiser la base de données :
```bash
python reset_db.py
```

6. Lancer l'application :
```bash
python app.py
```

7. Accéder à l'application dans votre navigateur :
```
http://localhost:5000
```

## Utilisation

### Première utilisation
1. Créer un compte enseignant
2. Se connecter avec les identifiants
3. Créer une ou plusieurs classes
4. Créer des exercices
5. Attribuer les exercices aux classes

### Pour les élèves
1. Créer un compte élève
2. Se connecter avec les identifiants
3. Rejoindre une classe avec le code fourni par l'enseignant
4. Accéder aux exercices de la classe
5. Réaliser les exercices

## Utilisation de Git et GitHub

### Configuration initiale de Git
```bash
# Configurer votre nom et email
git config --global user.name "Votre Nom"
git config --global user.email "votre.email@example.com"
```

### Commandes Git essentielles
```bash
# Vérifier l'état des fichiers
git status

# Ajouter des fichiers modifiés
git add .                  # Ajouter tous les fichiers
git add nomfichier.py      # Ajouter un fichier spécifique

# Créer un commit
git commit -m "Description des modifications"

# Pousser les modifications vers GitHub
git push origin main

# Récupérer les dernières modifications
git pull origin main

# Créer une nouvelle branche
git checkout -b nom-de-la-branche

# Changer de branche
git checkout nom-de-la-branche

# Fusionner une branche
git merge nom-de-la-branche
```

### Workflow Git typique
1. Avant de commencer à travailler :
```bash
git pull origin main
```

2. Créer une nouvelle branche pour vos modifications :
```bash
git checkout -b feature/nouvelle-fonctionnalite
```

3. Faire vos modifications et les commiter :
```bash
git add .
git commit -m "Description des modifications"
```

4. Pousser les modifications vers GitHub :
```bash
git push origin feature/nouvelle-fonctionnalite
```

5. Créer une Pull Request sur GitHub pour fusionner vos modifications

## Base de données

La base de données SQLite contient les tables suivantes :
- **Users** : Utilisateurs (enseignants et élèves)
- **Classes** : Classes créées par les enseignants
- **ClassEnrollments** : Inscriptions des élèves aux classes
- **Exercises** : Exercices avec leurs métadonnées
- **Questions** : Questions des exercices
- **Choices** : Options pour les QCM
- **TextHoles** : Trous pour les exercices de type texte à trous
- **ExerciseSubmissions** : Réponses des élèves

## Développement

### Réinitialiser la base de données
Pour repartir de zéro :
```bash
python reset_db.py
```

### Structure du projet
- `app.py` : Application principale Flask
- `models.py` : Modèles de la base de données
- `forms.py` : Formulaires WTForms
- `templates/` : Templates HTML
- `static/` : Fichiers statiques (CSS, JS, images)

## Technologies
- **Backend** : Flask (Python)
- **Base de données** : SQLite avec SQLAlchemy
- **Frontend** : 
  - HTML/CSS avec Bootstrap 5
  - JavaScript
  - Font Awesome pour les icônes
- **Sécurité** :
  - Flask-Login pour l'authentification
  - WTForms pour la validation des formulaires
  - Protection CSRF
