import os
import logging
from app import app, db, Exercise, PairMatch

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_image_paths():
    logger.info("Début de la mise à jour des chemins d'images")
    
    with app.app_context():
        # Récupérer tous les exercices de type pair_match
        exercises = Exercise.query.filter_by(exercise_type='pair_match').all()
        logger.info(f"Nombre d'exercices d'association trouvés : {len(exercises)}")
        
        for exercise in exercises:
            logger.info(f"\nTraitement de l'exercice {exercise.id}")
            
            for pair in exercise.pair_matches:
                # Mettre à jour le contenu gauche s'il s'agit d'une image
                if pair.left_type == 'image' and pair.left_content.startswith('uploads/'):
                    old_left_content = pair.left_content
                    pair.left_content = pair.left_content.replace('uploads/', '')
                    logger.info(f"Mise à jour du contenu gauche : {old_left_content} -> {pair.left_content}")
                
                # Mettre à jour le contenu droit s'il s'agit d'une image
                if pair.right_type == 'image' and pair.right_content.startswith('uploads/'):
                    old_right_content = pair.right_content
                    pair.right_content = pair.right_content.replace('uploads/', '')
                    logger.info(f"Mise à jour du contenu droit : {old_right_content} -> {pair.right_content}")
        
        # Sauvegarder les modifications
        try:
            db.session.commit()
            logger.info("\nMise à jour terminée avec succès")
        except Exception as e:
            db.session.rollback()
            logger.error(f"\nErreur lors de la mise à jour : {str(e)}")

if __name__ == '__main__':
    update_image_paths()
