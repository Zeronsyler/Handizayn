from flask import Flask, render_template, request, redirect, url_for, flash, Markup
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
except ImportError:
    print("Cloudinary import failed - check if package is installed")
import os
import markdown
from datetime import datetime
import logging
from sqlalchemy import text

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# PostgreSQL bağlantı URL'si
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://handizayn_user:3LkVstWfHrMV2f1r1nFYrfvRJbrJxT90@dpg-ctqfdartq21c73a0j4tg-a/handizayn')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Cloudinary yapılandırması
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', 'dy46noypm'),
    api_key=os.environ.get('CLOUDINARY_API_KEY', '264772451632922'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET', 'V29jE3GG-OftNLbdxv05-MJlbrA')
)

# Desteklenen resim formatları
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Veritabanı modellerini tanımla
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    products = db.relationship('Product', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'

    def save(self):
        if not self.slug:
            self.slug = slugify(self.name)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    images = db.relationship('ProductImage', backref='product', lazy=True, cascade="all, delete-orphan")

    def primary_image(self):
        return ProductImage.query.filter_by(product_id=self.id, is_primary=True).first() or \
               ProductImage.query.filter_by(product_id=self.id).first()

    def __repr__(self):
        return f'<Product {self.name}>'

class ProductImage(db.Model):
    __tablename__ = 'product_image'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(500), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)

    def __repr__(self):
        return f'<ProductImage {self.path}>'

class Image(db.Model):
    __tablename__ = 'image'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    section = db.Column(db.String(50), nullable=False)  # hero, about
    path = db.Column(db.String(500), nullable=False)

    def __repr__(self):
        return f'<Image {self.section}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    hero_image = Image.query.filter_by(section='hero').first()
    about_image = Image.query.filter_by(section='about').first()
    categories = Category.query.all()
    return render_template('index.html', 
                         hero_image=hero_image,
                         about_image=about_image,
                         categories=categories)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin'))
        flash('Geçersiz kullanıcı adı veya şifre')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    categories = Category.query.all()
    products = Product.query.all()
    images = {
        'hero': Image.query.filter_by(section='hero').first(),
        'about': Image.query.filter_by(section='about').first()
    }
    return render_template('admin.html', categories=categories, products=products, images=images)

@app.route('/admin/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            category_id = request.form.get('category')
            
            if not name or not category_id:
                flash('Lütfen gerekli alanları doldurun!', 'error')
                return redirect(url_for('admin'))
            
            # Ürünü oluştur
            product = Product(
                name=name,
                description=description,
                category_id=category_id
            )
            db.session.add(product)
            db.session.commit()
            
            # Görselleri kaydet
            files = request.files.getlist('images')
            is_first = True
            
            for file in files:
                if file and file.filename:
                    try:
                        # Cloudinary'ye yükle
                        upload_result = cloudinary.uploader.upload(file)
                        
                        # Ürün görselini oluştur
                        product_image = ProductImage(
                            path=upload_result['secure_url'],
                            is_primary=is_first,
                            product_id=product.id
                        )
                        db.session.add(product_image)
                        is_first = False
                    except Exception as e:
                        app.logger.error(f"Görsel yükleme hatası: {str(e)}")
                        continue
            
            db.session.commit()
            flash('Ürün başarıyla eklendi!', 'success')
            return redirect(url_for('admin'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Ürün ekleme hatası: {str(e)}")
            flash(f'Ürün eklenirken bir hata oluştu: {str(e)}', 'error')
            return redirect(url_for('admin'))
    
    categories = Category.query.all()
    return render_template('admin/add_product.html', categories=categories)

@app.route('/admin/upload_image', methods=['POST'])
@login_required
def upload_image():
    try:
        if 'image' not in request.files:
            flash('Dosya seçilmedi', 'error')
            return redirect(url_for('admin'))
        
        file = request.files['image']
        section = request.form.get('section')
        
        if not file or not file.filename or not section:
            flash('Lütfen bir dosya seçin ve section belirtin', 'error')
            return redirect(url_for('admin'))
        
        # Cloudinary'ye yükle
        upload_result = cloudinary.uploader.upload(file)
        
        # Mevcut görseli bul
        existing_image = Image.query.filter_by(section=section).first()
        
        if existing_image:
            # Mevcut görseli güncelle
            existing_image.path = upload_result['secure_url']
        else:
            # Yeni görsel oluştur
            image = Image(
                section=section,
                path=upload_result['secure_url']
            )
            db.session.add(image)
        
        db.session.commit()
        flash('Görsel başarıyla yüklendi!', 'success')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Görsel yükleme hatası: {str(e)}")
        flash(f'Görsel yüklenirken bir hata oluştu: {str(e)}', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin/add_images/<int:product_id>', methods=['POST'])
@login_required
def add_images(product_id):
    if 'images' not in request.files:
        flash('Dosya seçilmedi', 'error')
        return redirect(url_for('edit_product', id=product_id))
    
    files = request.files.getlist('images')
    
    try:
        for file in files:
            if file and file.filename:
                try:
                    # Cloudinary'ye yükle
                    result = cloudinary.uploader.upload(file)
                    
                    # Veritabanına kaydet
                    image = ProductImage(
                        path=result['secure_url'],
                        product_id=product_id
                    )
                    db.session.add(image)
                except Exception as e:
                    app.logger.error(f"Görsel yükleme hatası: {str(e)}")
                    continue
        
        db.session.commit()
        flash('Görseller başarıyla yüklendi!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Görsel yükleme hatası: {str(e)}")
        flash(f'Görsel yüklenirken bir hata oluştu: {str(e)}', 'error')
    
    return redirect(url_for('edit_product', id=product_id))

@app.route('/admin/edit_product/<int:id>', methods=['POST'])
def edit_product(id):
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.category_id = request.form['category']
        
        # Yeni resimleri yükle
        files = request.files.getlist('images')
        for file in files:
            if file and allowed_file(file.filename):
                try:
                    # Cloudinary'ye yükle
                    result = cloudinary.uploader.upload(file)
                    
                    # Veritabanına kaydet
                    image = ProductImage(
                        path=result['secure_url'],
                        product_id=product.id
                    )
                    db.session.add(image)
                except Exception as e:
                    app.logger.error(f"Görsel yükleme hatası: {str(e)}")
                    continue
        
        db.session.commit()
        flash('Ürün başarıyla güncellendi!', 'success')
        return redirect(url_for('admin'))
    
    return redirect(url_for('admin'))

@app.route('/admin/delete_product_image/<int:id>')
@login_required
def delete_product_image(id):
    image = ProductImage.query.get_or_404(id)
    
    # Cloudinary'den sil
    try:
        public_id = image.path.split('/')[-1].split('.')[0]
        cloudinary.uploader.destroy(public_id)
    except Exception as e:
        app.logger.error(f"Cloudinary silme hatası: {str(e)}")
    
    # Veritabanından sil
    db.session.delete(image)
    db.session.commit()
    
    flash('Resim başarıyla silindi!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete_section_image/<int:id>')
@login_required
def delete_section_image(id):
    image = Image.query.get_or_404(id)
    
    try:
        # Dosyayı sil
        file_path = os.path.join(app.root_path, 'static', image.path)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        app.logger.error(f"Dosya silme hatası: {str(e)}")
    
    # Veritabanından sil
    db.session.delete(image)
    db.session.commit()
    
    flash('Resim başarıyla silindi!', 'success')
    return redirect(url_for('admin'))

@app.route('/delete_product/<int:id>')
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    
    # Ürün görselini sil
    for image in product.images:
        image_path = os.path.join(app.root_path, 'static', image.path)
        if os.path.exists(image_path):
            os.remove(image_path)
    
    db.session.delete(product)
    db.session.commit()
    flash('Ürün başarıyla silindi')
    return redirect(url_for('admin'))

@app.route('/admin/category/<int:id>/delete', methods=['POST'])
@login_required
def delete_category(id):
    try:
        category = Category.query.get_or_404(id)
        
        # Kategoriye ait ürünleri kontrol et
        if category.products:
            flash('Bu kategoriye ait ürünler var. Önce ürünleri silmelisiniz.', 'error')
            return redirect(url_for('admin'))
            
        db.session.delete(category)
        db.session.commit()
        flash('Kategori başarıyla silindi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Kategori silinirken bir hata oluştu: {str(e)}', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin/category/add', methods=['POST'])
@login_required
def add_category():
    try:
        name = request.form.get('name')
        if not name:
            flash('Kategori adı boş olamaz', 'error')
            return redirect(url_for('admin'))
            
        category = Category(name=name)
        category.save()  # Slug'ı otomatik oluştur
        db.session.add(category)
        db.session.commit()
        flash('Kategori başarıyla eklendi', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Kategori eklenirken bir hata oluştu: {str(e)}', 'error')
    
    return redirect(url_for('admin'))

@app.route('/categories')
def categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

def slugify(text):
    text = text.lower()
    text = ''.join(c for c in text if c.isalnum() or c == ' ')
    text = '-'.join(text.split())
    return text

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
            
            # Slug kolonunu ekle
            add_slug_column()
            
        except Exception as e:
            db.session.rollback()
            print(f"Veritabanı başlatma hatası: {str(e)}")
            raise

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5004))
    app.run(host='0.0.0.0', port=port)
