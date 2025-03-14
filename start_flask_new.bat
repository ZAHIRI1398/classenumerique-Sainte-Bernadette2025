@echo off
call .\venv\Scripts\activate.bat
python migrate_db.py
python app_new.py
