from app import app, db, User, Category, slugify, text

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

def init_db():
    with app.app_context():
        try:
            # Tabloları oluştur
            db.create_all()
            
            # Admin kullanıcısını kontrol et ve oluştur
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin')
                admin.set_password('admin123')
                db.session.add(admin)
            
            # Varsayılan kategoriyi oluştur
            if not Category.query.first():
                default_category = Category(name='Genel')
                default_category.save()
                db.session.add(default_category)
            
            db.session.commit()
            print("Veritabanı başarıyla başlatıldı!")
            
            # Slug kolonunu ekle
            try:
                add_slug_column()
            except Exception as e:
                print(f"Slug kolonu zaten var olabilir: {str(e)}")
            
        except Exception as e:
            db.session.rollback()
            print(f"Veritabanı başlatma hatası: {str(e)}")

if __name__ == "__main__":
    init_db()
