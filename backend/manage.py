from app import create_app
from app.extensions import db

app = create_app()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "init-db":
        with app.app_context():
            db.create_all()
            print("Database tables created.")
    else:
        raise SystemExit("Use: python manage.py init-db")
