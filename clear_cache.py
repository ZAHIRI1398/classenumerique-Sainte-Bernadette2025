from app import app, db

def clear_cache():
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
        print("Cache SQLAlchemy nettoyé!")

if __name__ == '__main__':
    clear_cache()
