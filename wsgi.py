from app import app, init_db

# Veritabanını başlat
init_db()

if __name__ == "__main__":
    app.run()
