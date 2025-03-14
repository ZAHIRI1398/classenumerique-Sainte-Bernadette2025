@echo off
echo Quelle version de l'application souhaitez-vous démarrer ?
echo 1. Version originale (app.py)
echo 2. Nouvelle version (app_new.py)
choice /c 12 /n /m "Votre choix (1 ou 2) : "

if errorlevel 2 (
    echo Démarrage de la nouvelle version...
    call .\start_flask_new.bat
) else (
    echo Démarrage de la version originale...
    call .\start_flask.bat
)
