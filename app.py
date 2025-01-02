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
if os.environ.get('DATABASE_URL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace('postgres://', 'postgresql://')
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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    products = db.relationship('Product', back_populates='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = db.relationship('Category', back_populates='products', lazy=True)
    images = db.relationship('ProductImage', back_populates='product', lazy=True, cascade="all, delete-orphan")

    def primary_image(self):
        primary = next((img for img in self.images if img.is_primary), None)
        if primary is None and self.images:
            primary = self.images[0]
        return primary

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
    try:
        categories = Category.query.all()
        products = Product.query.all()
        
        # Görselleri section'lara göre grupla
        images_dict = {}
        all_images = Image.query.all()
        for image in all_images:
            images_dict[image.section] = image
            
        # Eğer bazı section'lar için görsel yoksa, None değeri ata
        required_sections = ['slider', 'about', 'contact']  # Gerekli section'lar
        for section in required_sections:
            if section not in images_dict:
                images_dict[section] = None
        
        return render_template('admin.html', 
                             categories=categories,
                             products=products,
                             images=images_dict)
    except Exception as e:
        app.logger.error(f"Admin sayfasında hata: {str(e)}")
        return f"Bir hata oluştu: {str(e)}", 500

@app.route('/admin/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category_id = request.form.get('category')
        files = request.files.getlist('images')
        
        if name and category_id:
            try:
                # Ürünü oluştur
                product = Product(
                    name=name,
                    description=description,
                    category_id=category_id
                )
                db.session.add(product)
                db.session.commit()
                
                # Görselleri kaydet
                is_first = True  # İlk resmi primary olarak işaretle
                for file in files:
                    if file.filename == '':
                        continue
                        
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
                
                db.session.commit()
                flash('Ürün başarıyla eklendi!', 'success')
                return redirect(url_for('admin_products'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ürün eklenirken bir hata oluştu: {str(e)}', 'error')
        else:
            flash('Lütfen gerekli alanları doldurun!', 'error')
    
    categories = Category.query.all()
    return render_template('admin/add_product.html', categories=categories)

@app.route('/admin/add_images/<int:product_id>', methods=['POST'])
@login_required
def add_images(product_id):
    if 'images' not in request.files:
        flash('Dosya seçilmedi', 'error')
        return redirect(url_for('edit_product', id=product_id))
    
    files = request.files.getlist('images')
    
    try:
        for file in files:
            if file.filename == '':
                continue
            
            # Cloudinary'ye yükle
            result = cloudinary.uploader.upload(file)
            
            # Veritabanına kaydet
            image = ProductImage(
                path=result['secure_url'],
                product_id=product_id
            )
            db.session.add(image)
        
        db.session.commit()
        flash('Görseller başarıyla yüklendi!', 'success')
    except Exception as e:
        db.session.rollback()
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
                # Cloudinary'ye yükle
                try:
                    result = cloudinary.uploader.upload(file)
                except Exception as e:
                    print(f"Cloudinary upload failed: {e}")
                    continue
                
                # Veritabanına kaydet
                image = ProductImage(
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
    try:
        if 'image' not in request.files:
            flash('Görsel seçilmedi')
            return redirect(url_for('admin'))
        
        file = request.files['image']
        section = request.form.get('section')
        
        if file.filename == '':
            flash('Görsel seçilmedi')
            return redirect(url_for('admin'))
            
        if file and section and allowed_file(file.filename):
            try:
                # Cloudinary'ye yükle
                upload_result = cloudinary.uploader.upload(file)
                
                # Varolan görseli güncelle veya yeni görsel oluştur
                image = Image.query.filter_by(section=section).first()
                if image:
                    image.path = upload_result['secure_url']
                else:
                    image = Image(
                        filename=file.filename,
                        section=section, 
                        path=upload_result['secure_url']
                    )
                    db.session.add(image)
                
                db.session.commit()
                flash('Görsel başarıyla yüklendi')
                
            except Exception as e:
                app.logger.error(f"Görsel yükleme hatası: {str(e)}")
                flash(f'Görsel yüklenirken bir hata oluştu: {str(e)}', 'error')
                
    except Exception as e:
        app.logger.error(f"Görsel yükleme işleminde hata: {str(e)}")
        flash(f'Bir hata oluştu: {str(e)}', 'error')
    
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

@app.route('/categories')
def categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

def slugify(text):
    text = text.lower()
    text = ''.join(c for c in text if c.isalnum() or c == ' ')
    text = '-'.join(text.split())
    return text

def init_db():
    with app.app_context():
        try:
            # Mevcut tabloları sil
            db.drop_all()
            
            # Yeni tabloları oluştur
            db.create_all()
            
            # Admin kullanıcısını oluştur
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin')
                admin.set_password('admin123')
                db.session.add(admin)
            
            # Varsayılan kategoriyi oluştur
            if not Category.query.first():
                default_category = Category(name='Genel')
                db.session.add(default_category)
            
            db.session.commit()
            print("Veritabanı başarıyla oluşturuldu!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Veritabanı oluşturulurken hata: {str(e)}")

if __name__ == '__main__':
    init_db()  # Veritabanını yeniden oluştur
    
    port = int(os.environ.get('PORT', 5004))
    app.run(host='0.0.0.0', port=port)
