import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Création du dossier logs s'il n'existe pas
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configuration du logger principal
logger = logging.getLogger('classe_numerique')
logger.setLevel(logging.DEBUG)

# Format du log
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(module)s:%(lineno)d - %(message)s'
)

# Handler pour fichier avec rotation (nouveau fichier chaque jour)
log_filename = f'logs/app_{datetime.now().strftime("%Y-%m-%d")}.log'
file_handler = RotatingFileHandler(log_filename, maxBytes=10485760, backupCount=5)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Handler pour la console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Ajout des handlers au logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def log_database_error(error, context=""):
    """Log les erreurs de base de données"""
    logger.error(f"Database Error in {context}: {str(error)}")
    logger.exception(error)

def log_form_data(form_data, route):
    """Log les données de formulaire reçues"""
    logger.debug(f"Form data received in {route}: {form_data}")

def log_model_creation(model_name, data):
    """Log la création d'un nouveau modèle"""
    logger.info(f"Creating new {model_name} with data: {data}")

def log_model_update(model_name, model_id, changes):
    """Log la mise à jour d'un modèle"""
    logger.info(f"Updating {model_name} (ID: {model_id}) with changes: {changes}")

def log_request_info(request):
    """Log les informations de la requête"""
    logger.debug(f"""
    Request Info:
    - Method: {request.method}
    - Path: {request.path}
    - Args: {request.args}
    - Form: {request.form}
    - JSON: {request.get_json(silent=True)}
    """)
