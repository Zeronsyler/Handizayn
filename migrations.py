from app import app, db
from sqlalchemy import text

def drop_filename_column():
    with app.app_context():
        try:
            # Mevcut tabloyu yedekle
            db.session.execute(text('CREATE TABLE product_image_backup AS SELECT id, path, is_primary, product_id FROM product_image;'))
            
            # Eski tabloyu sil
            db.session.execute(text('DROP TABLE product_image;'))
            
            # Yeni tabloyu oluştur
            db.session.execute(text('''
                CREATE TABLE product_image (
                    id SERIAL PRIMARY KEY,
                    path VARCHAR(500) NOT NULL,
                    is_primary BOOLEAN DEFAULT FALSE,
                    product_id INTEGER NOT NULL REFERENCES product(id) ON DELETE CASCADE
                );
            '''))
            
            # Verileri geri yükle
            db.session.execute(text('INSERT INTO product_image (id, path, is_primary, product_id) SELECT id, path, is_primary, product_id FROM product_image_backup;'))
            
            # Yedek tabloyu sil
            db.session.execute(text('DROP TABLE product_image_backup;'))
            
            # Sequence'i düzelt
            db.session.execute(text("SELECT setval('product_image_id_seq', (SELECT MAX(id) FROM product_image));"))
            
            db.session.commit()
            print("Migration başarıyla tamamlandı!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Migration hatası: {str(e)}")
            raise

if __name__ == "__main__":
    drop_filename_column()
