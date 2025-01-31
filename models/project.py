from datetime import datetime
from models.user import db

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='active')  # active/completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Информация о заказчике
    client_type = db.Column(db.String(20))  # individual/legal
    client_name = db.Column(db.String(255))
    client_passport = db.Column(db.String(20))
    company_name = db.Column(db.String(255))
    company_inn = db.Column(db.String(12))
    company_ogrn = db.Column(db.String(15))
    client_phone = db.Column(db.String(20))
    client_email = db.Column(db.String(120))
    client_address = db.Column(db.Text)
    
    # Связь с пользователем
    user = db.relationship('User', backref=db.backref('projects', lazy=True))
    
    @property
    def objects_count(self):
        # TODO: Добавить связь с объектами проекта
        return 0 