from app import app, db
from sqlalchemy import text
from app import slugify

def add_slug_column():
    with app.app_context():
        try:
            # Mevcut tabloyu yedekle
            db.session.execute(text('CREATE TABLE category_backup AS SELECT * FROM category;'))
            
            # Eski tabloyu sil
            db.session.execute(text('DROP TABLE category CASCADE;'))
            
            # Yeni tabloyu oluştur
            db.session.execute(text('''
                CREATE TABLE category (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(200) NOT NULL UNIQUE,
                    slug VARCHAR(200) NOT NULL UNIQUE
                );
            '''))
            
            # Verileri geri yükle ve slug'ları oluştur
            result = db.session.execute(text('SELECT id, name FROM category_backup;'))
            for row in result:
                slug = slugify(row[1])  # row[1] is name
                db.session.execute(
                    text('INSERT INTO category (id, name, slug) VALUES (:id, :name, :slug)'),
                    {'id': row[0], 'name': row[1], 'slug': slug}
                )
            
            # Sequence'i düzelt
            db.session.execute(text("SELECT setval('category_id_seq', (SELECT MAX(id) FROM category));"))
            
            # Yedek tabloyu sil
            db.session.execute(text('DROP TABLE category_backup;'))
            
            db.session.commit()
            print("Migration başarıyla tamamlandı!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Migration hatası: {str(e)}")
            raise

if __name__ == "__main__":
    add_slug_column()
