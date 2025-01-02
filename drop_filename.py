from app import app, db
from sqlalchemy import text

with app.app_context():
    db.session.execute(text('ALTER TABLE product_image DROP COLUMN IF EXISTS filename;'))
    db.session.commit()
    print("filename column dropped successfully!")
