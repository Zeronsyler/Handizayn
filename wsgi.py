from app import app

# Gunicorn için app değişkenini export et
application = app

if __name__ == "__main__":
    app.run()
