from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from flask import Markup
import markdown

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Veritabanı yapılandırması
if os.environ.get('FLASK_ENV') == 'production':
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    products = db.relationship('Product', backref='category', lazy=True)

    def __init__(self, name):
        self.name = name
        self.slug = slugify(name)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    images = db.relationship('ProductImage', backref='product', lazy=True, cascade="all, delete-orphan")

    def primary_image(self):
        primary = next((img for img in self.images if img.is_primary), None)
        return primary if primary else (self.images[0] if self.images else None)

    def __str__(self):
        return f"{self.name} - {self.category_id}"

class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    path = db.Column(db.String(200), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)  # Ana görsel mi?
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

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
    images = Image.query.all()
    products = Product.query.all()
    categories = Category.query.all()
    return render_template('admin.html', images=images, products=products, categories=categories)

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

@app.route('/add_product', methods=['POST'])
@login_required
def add_product():
    name = request.form.get('name')
    description = request.form.get('description')
    category_id = request.form.get('category_id')
    files = request.files.getlist('images')
    
    if not name or not category_id or not files:
        flash('Tüm alanları doldurun')
        return redirect(url_for('admin'))
    
    product = Product(
        name=name,
        description=description,
        category_id=category_id
    )
    db.session.add(product)
    
    # Görselleri kaydet
    for i, file in enumerate(files):
        if file:
            filename = secure_filename(file.filename)
            products_folder = os.path.join(app.root_path, 'static', 'images', 'products')
            
            if not os.path.exists(products_folder):
                os.makedirs(products_folder)
                
            file_path = os.path.join(products_folder, filename)
            file.save(file_path)
            
            product_image = ProductImage(
                filename=filename,
                path=os.path.join('images', 'products', filename),
                is_primary=(i == 0),  # İlk görsel ana görsel olsun
                product=product
            )
            db.session.add(product_image)
    
    db.session.commit()
    flash('Ürün başarıyla eklendi')
    return redirect(url_for('admin'))

@app.route('/edit_product/<int:id>', methods=['POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    
    product.name = request.form.get('name')
    product.description = request.form.get('description')
    product.category_id = request.form.get('category_id')
    
    files = request.files.getlist('images')
    if files and files[0].filename != '':
        for i, file in enumerate(files):
            filename = secure_filename(file.filename)
            products_folder = os.path.join(app.root_path, 'static', 'images', 'products')
            
            if not os.path.exists(products_folder):
                os.makedirs(products_folder)
                
            file_path = os.path.join(products_folder, filename)
            file.save(file_path)
            
            product_image = ProductImage(
                filename=filename,
                path=os.path.join('images', 'products', filename),
                is_primary=(i == 0 and not product.images),  # Eğer hiç görsel yoksa ilk görsel ana görsel olsun
                product=product
            )
            db.session.add(product_image)
    
    db.session.commit()
    flash('Ürün başarıyla güncellendi')
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

@app.route('/delete_product_image/<int:id>')
@login_required
def delete_product_image(id):
    image = ProductImage.query.get_or_404(id)
    product = image.product
    
    # Görseli diskten sil
    file_path = os.path.join(app.root_path, 'static', image.path)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Eğer silinen görsel ana görsel ise ve başka görseller varsa, ilk görseli ana görsel yap
    if image.is_primary and product.images:
        next_image = next((img for img in product.images if img.id != image.id), None)
        if next_image:
            next_image.is_primary = True
    
    db.session.delete(image)
    db.session.commit()
    
    flash('Görsel başarıyla silindi')
    return redirect(url_for('admin'))

@app.route('/delete_image/<section>')
@login_required
def delete_image(section):
    image = Image.query.filter_by(section=section).first()
    if image:
        # Görseli dosya sisteminden sil
        image_path = os.path.join(app.root_path, 'static', image.path)
        if os.path.exists(image_path):
            os.remove(image_path)
        
        # Veritabanından sil
        db.session.delete(image)
        db.session.commit()
        flash(f'{section.title()} görseli başarıyla silindi')
    
    return redirect(url_for('admin'))

@app.route('/add_category', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name')
    if name:
        if not Category.query.filter_by(name=name).first():
            category = Category(name=name)
            db.session.add(category)
            db.session.commit()
            flash('Kategori başarıyla eklendi')
        else:
            flash('Bu kategori zaten mevcut')
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

def slugify(text):
    text = text.lower()
    text = ''.join(c for c in text if c.isalnum() or c == ' ')
    text = '-'.join(text.split())
    return text

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

def init_default_categories():
    default_categories = ['Modern', 'Geleneksel', 'Vintage', 'Özel Tasarım']
    
    for category_name in default_categories:
        if not Category.query.filter_by(name=category_name).first():
            category = Category(name=category_name)
            db.session.add(category)
    
    db.session.commit()

def init_admin_user():
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.password_hash = generate_password_hash('admin123')
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_admin_user()
        init_default_categories()
        init_default_images()
    
    port = int(os.environ.get('PORT', 5004))
    if os.environ.get('FLASK_ENV') == 'production':
        app.run(host='0.0.0.0', port=port)
    else:
        app.run(debug=True, port=port)
