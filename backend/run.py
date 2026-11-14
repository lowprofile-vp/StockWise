import os

from app import create_app

app = create_app("production" if os.getenv("FLASK_ENV") == "production" else "default")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
