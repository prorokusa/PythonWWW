from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)  # Email будет использоваться как username
    password_hash = db.Column(db.String(128))
    projects_folder = db.Column(db.String(255), unique=True)  # Путь к папке с проектами пользователя
    
    # Персональные данные
    full_name = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    
    # Профессиональные данные
    snils = db.Column(db.String(14))
    registration_number = db.Column(db.String(50))
    sro_membership = db.Column(db.String(255))
    
    # Данные организации
    organization_name = db.Column(db.String(255))
    organization_inn = db.Column(db.String(12))
    organization_ogrn = db.Column(db.String(15))
    organization_address = db.Column(db.Text)
    organization_contact = db.Column(db.String(255))
    
    # Данные оборудования
    device_type = db.Column(db.String(255))
    device_serial = db.Column(db.String(50))
    device_verification_date = db.Column(db.Date)
    
    # Флаг первого входа
    is_first_login = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password) 