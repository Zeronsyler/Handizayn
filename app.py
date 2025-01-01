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

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Cloudinary yapılandırması
try:
    cloudinary.config(
        cloud_name='dy46noypm',
        api_key='264772451632922',
        api_secret='V29jE3GG-OftNLbdxv05-MJlbrA'
    )
except Exception as e:
    print(f"Cloudinary configuration failed: {e}")

# Desteklenen resim formatları
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Veritabanı yapılandırması
if os.environ.get('FLASK_ENV') == 'production':
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Veritabanı modellerini tanımla
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    products = db.relationship('Product', back_populates='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = db.relationship('Category', back_populates='products', lazy=True)
    images = db.relationship('ProductImage', back_populates='product', lazy=True, cascade="all, delete-orphan")

    def primary_image(self):
        return next((img for img in self.images if img.is_primary), self.images[0] if self.images else None)

    def __repr__(self):
        return f'<Product {self.name}>'

class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(500), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product', back_populates='images')

    def __repr__(self):
        return f'<ProductImage {self.path}>'

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    section = db.Column(db.String(50), nullable=False)
    path = db.Column(db.String(200), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    products = Product.query.all()
    categories = Category.query.all()
    hero_image = Image.query.filter_by(section='hero').first()
    about_image = Image.query.filter_by(section='about').first()
    return render_template('index.html', 
                         products=products, 
                         categories=categories,
                         hero_image=hero_image,
                         about_image=about_image)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
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
    products = Product.query.all()
    categories = Category.query.all()
    
    # Bölüm görsellerini getir
    section_images = {}
    for section in ['hero', 'about']:
        image = Image.query.filter_by(section=section).first()
        section_images[section] = image
    
    return render_template('admin.html', 
                         products=products, 
                         categories=categories,
                         images=section_images)

@app.route('/admin/add_product', methods=['POST'])
@login_required
def add_product():
    try:
        name = request.form['name']
        description = request.form['description']
        category_id = request.form['category']
        files = request.files.getlist('images')
        
        if not files:
            flash('Lütfen en az bir resim seçin!', 'error')
            return redirect(url_for('admin'))
        
        # Ürünü oluştur
        product = Product(
            name=name,
            description=description,
            category_id=category_id
        )
        db.session.add(product)
        db.session.commit()
        
        # Resimleri yükle
        for i, file in enumerate(files):
            if file and allowed_file(file.filename):
                try:
                    print(f"Uploading file: {file.filename}")
                    # Cloudinary'ye yükle
                    result = cloudinary.uploader.upload(file)
                    print(f"Cloudinary result: {result}")
                    
                    # Veritabanına kaydet
                    image = ProductImage(
                        path=result['secure_url'],
                        product_id=product.id,
                        is_primary=(i == 0)
                    )
                    db.session.add(image)
                    print(f"Added image to database: {image.path}")
                except Exception as e:
                    print(f"Error uploading to Cloudinary: {str(e)}")
                    continue
        
        db.session.commit()
        flash('Ürün başarıyla eklendi!', 'success')
    except Exception as e:
        print(f"Error in add_product: {str(e)}")
        db.session.rollback()
        flash(f'Ürün eklenirken bir hata oluştu: {str(e)}', 'error')
    
    return redirect(url_for('admin'))

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
                # Cloudinary'ye yükle
                try:
                    result = cloudinary.uploader.upload(file)
                except Exception as e:
                    print(f"Cloudinary upload failed: {e}")
                    continue
                
                # Veritabanına kaydet
                image = ProductImage(
                    filename=file.filename,
                    path=result['secure_url'],
                    product_id=product.id
                )
                db.session.add(image)
        
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
        print(f"Cloudinary delete failed: {e}")
    
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
        print(f"Error deleting file: {e}")
    
    # Veritabanından sil
    db.session.delete(image)
    db.session.commit()
    
    flash('Resim başarıyla silindi!', 'success')
    return redirect(url_for('admin'))

@app.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    if 'image' not in request.files:
        flash('Görsel seçilmedi')
        return redirect(url_for('admin'))
    
    file = request.files['image']
    section = request.form.get('section')
    
    if file.filename == '':
        flash('Görsel seçilmedi')
        return redirect(url_for('admin'))
        
    if file and section:
        filename = secure_filename(file.filename)
        section_folder = os.path.join(app.root_path, 'static', 'images', section)
        
        # Klasör yoksa oluştur
        if not os.path.exists(section_folder):
            os.makedirs(section_folder)
        
        file_path = os.path.join(section_folder, filename)
        file.save(file_path)
        
        # Varolan görseli güncelle veya yeni görsel oluştur
        image = Image.query.filter_by(section=section).first()
        if image:
            # Eski dosyayı sil
            old_file = os.path.join(app.root_path, 'static', image.path)
            if os.path.exists(old_file):
                os.remove(old_file)
            image.path = os.path.join('images', section, filename)
        else:
            image = Image(section=section, path=os.path.join('images', section, filename))
            db.session.add(image)
        
        db.session.commit()
        flash('Görsel başarıyla yüklendi')
    
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

@app.route('/delete_category/<int:id>')
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    if Product.query.filter_by(category_id=id).first():
        flash('Bu kategoriye ait ürünler var. Önce ürünleri silmelisiniz.')
    else:
        db.session.delete(category)
        db.session.commit()
        flash('Kategori başarıyla silindi')
    return redirect(url_for('admin'))

@app.route('/admin/add_category', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name')
    if name:
        existing_category = Category.query.filter_by(name=name).first()
        if not existing_category:
            category = Category(name=name)
            db.session.add(category)
            db.session.commit()
            flash('Kategori başarıyla eklendi')
        else:
            flash('Bu kategori zaten mevcut')
    return redirect(url_for('admin'))

@app.route('/admin/make_primary/<int:product_id>/<int:image_id>')
@login_required
def make_primary_image(product_id, image_id):
    product = Product.query.get_or_404(product_id)
    
    # Önce tüm resimlerin primary özelliğini false yap
    for image in product.images:
        image.is_primary = False
    
    # Seçilen resmi primary yap
    image = ProductImage.query.get_or_404(image_id)
    image.is_primary = True
    
    db.session.commit()
    flash('Ana görsel başarıyla güncellendi!', 'success')
    return redirect(url_for('admin'))

def slugify(text):
    text = text.lower()
    text = ''.join(c for c in text if c.isalnum() or c == ' ')
    text = '-'.join(text.split())
    return text

def create_tables():
    with app.app_context():
        db.create_all()
        # Admin kullanıcısını oluştur
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.password_hash = generate_password_hash('admin123')
            db.session.add(admin)
            db.session.commit()
        
        # Varsayılan kategorileri oluştur
        if not Category.query.first():
            categories = ['Modern', 'Klasik', 'Vintage', 'El Dokuma', 'Özel Tasarım']
            for cat_name in categories:
                category = Category(name=cat_name)
                db.session.add(category)
            db.session.commit()

def init_default_images():
    # Hero görseli
    if not Image.query.filter_by(section='hero').first():
        hero_image = Image(
            section='hero',
            path='images/hero/hero.jpg'
        )
        db.session.add(hero_image)

    # About görseli
    if not Image.query.filter_by(section='about').first():
        about_image = Image(
            section='about',
            path='images/about/about.jpg'
        )
        db.session.add(about_image)

    db.session.commit()

def init_admin_user():
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.password_hash = generate_password_hash('admin123')
        db.session.add(admin)
        db.session.commit()

create_tables()

if __name__ == '__main__':
    init_default_images()
    init_admin_user()
    port = int(os.environ.get('PORT', 5004))
    if os.environ.get('FLASK_ENV') == 'production':
        app.run(host='0.0.0.0', port=port)
    else:
        app.run(debug=True, port=port)
