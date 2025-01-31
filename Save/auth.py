from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models.user import User, db
import os

auth = Blueprint('auth', __name__)
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([username, email, password, confirm_password]):
            flash('Все поля должны быть заполнены', 'error')
            return redirect(url_for('auth.register'))
            
        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return redirect(url_for('auth.register'))
            
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        # Создаем персональную папку для проектов пользователя
        projects_folder = os.path.join('projects', username)
        os.makedirs(projects_folder, exist_ok=True)
        new_user.projects_folder = projects_folder
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Регистрация успешна! Теперь вы можете войти', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not all([username, password]):
            flash('Все поля должны быть заполнены', 'error')
            return redirect(url_for('auth.login'))
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
            
        flash('Неверное имя пользователя или пароль', 'error')
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы', 'success')
    return redirect(url_for('index'))

# Настройка обработчика для неавторизованных пользователей
@login_manager.unauthorized_handler
def unauthorized():
    flash('Для доступа к этой странице необходимо войти в систему', 'error')
    return redirect(url_for('auth.login')) 