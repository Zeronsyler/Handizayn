# Veritabanını sıfırlamak için script oluşturuyorum
from app import app, db, init_db

with app.app_context():
    db.drop_all()
    db.create_all()
    init_db()
    print("Veritabanı başarıyla sıfırlandı!")
