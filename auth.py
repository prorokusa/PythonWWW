from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models.user import User, db
import os
from datetime import datetime

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
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        terms = request.form.get('terms')
        
        if not all([full_name, email, password, confirm_password]):
            flash('Все обязательные поля должны быть заполнены', 'error')
            return redirect(url_for('auth.register'))
            
        if not terms:
            flash('Необходимо принять условия пользовательского соглашения', 'error')
            return redirect(url_for('auth.register'))
            
        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return redirect(url_for('auth.register'))
            
        new_user = User(
            email=email,  # email будет использоваться как username
            full_name=full_name,
            phone=phone,
            is_first_login=True
        )
        new_user.set_password(password)
        
        # Создаем персональную папку для проектов пользователя
        projects_folder = os.path.join('projects', email)
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
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('dashboard')
            return redirect(next_page)
            
        flash('Неверный email или пароль', 'error')
        
    return render_template('login.html')

@auth.route('/onboarding')
@login_required
def onboarding():
    return render_template('onboarding.html', step=1)

@auth.route('/setup_profile', methods=['GET', 'POST'])
@login_required
def setup_profile():
    if request.method == 'POST':
        try:
            # Обновляем данные пользователя
            current_user.full_name = request.form.get('full_name')
            current_user.snils = request.form.get('snils')
            current_user.registration_number = request.form.get('registration_number')
            current_user.sro_membership = request.form.get('sro_membership')
            
            current_user.organization_name = request.form.get('organization_name')
            current_user.organization_inn = request.form.get('organization_inn')
            current_user.organization_ogrn = request.form.get('organization_ogrn')
            current_user.organization_address = request.form.get('organization_address')
            current_user.organization_contact = request.form.get('organization_contact')
            
            current_user.device_type = request.form.get('device_type')
            current_user.device_serial = request.form.get('device_serial')
            
            verification_date = request.form.get('device_verification_date')
            if verification_date:
                current_user.device_verification_date = datetime.strptime(verification_date, '%Y-%m-%d')
            
            # Отмечаем, что первый вход завершен
            current_user.is_first_login = False
            
            db.session.commit()
            flash('Профиль успешно настроен!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Ошибка при сохранении данных: {str(e)}', 'error')
            return redirect(url_for('auth.setup_profile'))
    
    return render_template('setup_profile.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы', 'success')
    return redirect(url_for('index'))

@auth.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Здесь будет логика отправки email для сброса пароля
            flash('Инструкции по сбросу пароля отправлены на ваш email', 'success')
            return redirect(url_for('auth.login'))
            
        flash('Email не найден', 'error')
    return render_template('reset_password_request.html')

# Настройка обработчика для неавторизованных пользователей
@login_manager.unauthorized_handler
def unauthorized():
    flash('Для доступа к этой странице необходимо войти в систему', 'error')
    return redirect(url_for('auth.login')) 