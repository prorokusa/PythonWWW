from flask import Flask
from flask_login import LoginManager
from models.user import db
from auth import auth, login_manager
from main1 import init_routes

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Для сессий и безопасности
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Users.db'

# Инициализация расширений
db.init_app(app)
login_manager.init_app(app)

# Регистрация blueprint'ов
app.register_blueprint(auth)

# Инициализация маршрутов проектов
init_routes(app)

# Создание таблиц при первом запуске
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)