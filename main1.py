from flask import render_template, request, jsonify, redirect, url_for, flash
import sqlite3
from pathlib import Path
import os
from flask_login import login_required, current_user
from datetime import datetime

# Папка для хранения баз данных проектов
PROJECTS_DIR = Path("projects")
PROJECTS_DIR.mkdir(exist_ok=True)

def get_user_folder(username):
    """Получить путь к папке проектов пользователя"""
    user_folder = PROJECTS_DIR / username
    user_folder.mkdir(exist_ok=True)
    return user_folder

# Последовательность вопросов
QUESTIONS = [
    "Введите имя проекта",
    "Введите расстояние до объекта (км)",
    "Введите стоимость километра (руб)"
]

def get_user_projects(user_folder):
    """Получить проекты конкретного пользователя"""
    projects = []
    user_projects_dir = Path(user_folder)
    
    if not user_projects_dir.exists():
        return projects
        
    for db_file in user_projects_dir.glob("*.db"):
        try:
            conn = sqlite3.connect(str(db_file))
            c = conn.cursor()
            
            # Сначала проверим существующие колонки
            c.execute("PRAGMA table_info(project_data)")
            columns = [column[1] for column in c.fetchall()]
            
            # Формируем SQL запрос на основе существующих колонок
            select_columns = ['project_name', 'display_name', 'status', 'created_at']
            if 'updated_at' in columns:
                select_columns.append('updated_at')
            if 'client_type' in columns:
                select_columns.append('client_type')
            if 'client_name' in columns:
                select_columns.append('client_name')
            if 'company_name' in columns:
                select_columns.append('company_name')
            if 'company_inn' in columns:
                select_columns.append('company_inn')
            
            query = f"""
                SELECT {', '.join(select_columns)}
                FROM project_data
                WHERE id = 1
            """
            
            c.execute(query)
            row = c.fetchone()
            
            if row:
                # Получаем количество объектов
                c.execute("SELECT COUNT(*) FROM project_objects")
                objects_count = c.fetchone()[0]
                
                # Создаем словарь проекта с безопасными значениями по умолчанию
                project_data = {
                    'project_name': row[0],
                    'display_name': row[1] or row[0],
                    'status': row[2],
                    'created_at': row[3],
                    'updated_at': row[4] if len(row) > 4 else None,
                    'client_type': row[5] if len(row) > 5 else None,
                    'client_name': row[6] if len(row) > 6 else None,
                    'company_name': row[7] if len(row) > 7 else None,
                    'company_inn': row[8] if len(row) > 8 else None,
                    'objects_count': objects_count
                }
                
                projects.append(project_data)
            
            conn.close()
        except sqlite3.Error as e:
            print(f"Error reading project: {e}")
            continue
            
    return projects

def get_project_db_path(project_name, user_folder):
    """Получить путь к базе данных проекта пользователя"""
    return Path(user_folder) / f"{project_name}.db"

def init_project_db(project_name, user_folder):
    """Инициализация базы данных для проекта пользователя"""
    db_path = get_project_db_path(project_name, user_folder)
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    # Создаем таблицу с правильной структурой
    c.execute('''
        CREATE TABLE IF NOT EXISTS project_data
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         project_name TEXT,
         display_name TEXT,
         status TEXT DEFAULT 'active',
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         
         -- Информация о заказчике
         client_type TEXT,
         client_name TEXT,
         client_passport TEXT,
         company_name TEXT,
         company_inn TEXT,
         company_ogrn TEXT,
         client_phone TEXT,
         client_email TEXT,
         client_address TEXT,
         
         -- Данные проекта
         distance REAL,
         cost_per_km REAL,
         total_cost REAL)
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS project_objects
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         name TEXT,
         status TEXT DEFAULT 'active',
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         message_type TEXT,
         content TEXT,
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         object_id INTEGER,
         FOREIGN KEY(object_id) REFERENCES project_objects(id))
    ''')
    
    conn.commit()
    conn.close()

def update_project_data(project_name, field, value, user_folder):
    """Обновить данные проекта пользователя"""
    db_path = get_project_db_path(project_name, user_folder)
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    try:
        c.execute(f"UPDATE project_data SET {field} = ? WHERE id = 1", (value,))
        
        if field in ['distance', 'cost_per_km']:
            c.execute("SELECT distance, cost_per_km FROM project_data WHERE id = 1")
            distance, cost_per_km = c.fetchone()
            
            if distance is not None and cost_per_km is not None:
                total_cost = float(distance) * float(cost_per_km)
                c.execute("UPDATE project_data SET total_cost = ? WHERE id = 1", (total_cost,))
        
        conn.commit()
        
        c.execute("""
            SELECT project_name, display_name, distance, cost_per_km, total_cost 
            FROM project_data 
            WHERE id = 1
        """)
        row = c.fetchone()
        updated_data = {
            'project_name': row[0],
            'display_name': row[1],
            'distance': row[2],
            'cost_per_km': row[3],
            'total_cost': row[4]
        }
        return updated_data
    finally:
        conn.close()

def create_new_project(user_folder, project_data):
    """Создание нового проекта"""
    project_name = project_data['project_name'].lower().replace(' ', '_')
    db_path = get_project_db_path(project_name, user_folder)
    
    if db_path.exists():
        raise ValueError("Проект с таким именем уже существует")
    
    init_project_db(project_name, user_folder)
    
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO project_data 
        (project_name, display_name, client_type, client_name, client_passport,
         company_name, company_inn, company_ogrn, client_phone, client_email,
         client_address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project_name,
        project_data['project_name'],
        project_data['client_type'],
        project_data.get('client_name'),
        project_data.get('client_passport'),
        project_data.get('company_name'),
        project_data.get('company_inn'),
        project_data.get('company_ogrn'),
        project_data['client_phone'],
        project_data.get('client_email'),
        project_data.get('client_address')
    ))
    
    conn.commit()
    conn.close()
    return project_name

def get_project_details(project_name, user_folder):
    """Получение данных проекта"""
    db_path = get_project_db_path(project_name, user_folder)
    if not db_path.exists():
        return None
        
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    c.execute("SELECT * FROM project_data WHERE id = 1")
    columns = [description[0] for description in c.description]
    row = c.fetchone()
    
    if row:
        project = dict(zip(columns, row))
        
        # Получаем количество объектов
        c.execute("SELECT COUNT(*) FROM project_objects")
        project['objects_count'] = c.fetchone()[0]
        
        conn.close()
        return project
    
    conn.close()
    return None

def update_project(project_name, user_folder, project_data):
    """Обновление данных проекта"""
    db_path = get_project_db_path(project_name, user_folder)
    if not db_path.exists():
        raise ValueError("Проект не найден")
        
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    try:
        # Добавляем updated_at к обновляемым полям
        project_data['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        update_fields = []
        values = []
        
        for field, value in project_data.items():
            if field != 'project_name':  # Не обновляем project_name, так как это ключ
                update_fields.append(f"{field} = ?")
                values.append(value)
        
        if update_fields:
            query = f"""
                UPDATE project_data 
                SET {', '.join(update_fields)}
                WHERE id = 1
            """
            c.execute(query, values)
            conn.commit()
            
        return True
    finally:
        conn.close()

def init_routes(app):
    """Инициализация всех маршрутов"""
    
    # 1. Основные страницы
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        projects = get_user_projects(current_user.projects_folder)
        return render_template('dashboard.html', 
                             projects=projects,
                             current_question=QUESTIONS[0])

    @app.route('/projects')
    @login_required
    def projects():
        user_projects = get_user_projects(current_user.projects_folder)
        return render_template('projects.html', projects=user_projects)

    # 2. CRUD операции с проектами
    @app.route('/create_project', methods=['GET', 'POST'])
    @login_required
    def create_project():
        if request.method == 'POST':
            try:
                project_data = {
                    'project_name': request.form['project_name'],
                    'client_type': 'individual',  # значение по умолчанию
                    'client_phone': '',  # пустые значения
                    'client_email': '',
                    'client_name': '',
                    'company_name': '',
                    'company_inn': '',
                    'company_ogrn': '',
                    'status': 'active'  # статус по умолчанию
                }
                
                create_new_project(current_user.projects_folder, project_data)
                flash('Проект успешно создан!', 'success')
                return redirect(url_for('projects'))
                
            except Exception as e:
                flash(f'Ошибка при создании проекта: {str(e)}', 'error')
                return redirect(url_for('dashboard'))

        return render_template('create_project.html')

    @app.route('/project/<project_name>')
    @login_required
    def view_project(project_name):
        project = get_project_details(project_name, current_user.projects_folder)
        if not project:
            flash('Проект не найден', 'error')
            return redirect(url_for('projects'))
        return render_template('project_detail.html', project=project)

    @app.route('/project/<project_name>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_project(project_name):
        project = get_project_details(project_name, current_user.projects_folder)
        if not project:
            flash('Проект не найден', 'error')
            return redirect(url_for('projects'))
        
        if request.method == 'POST':
            try:
                project_data = {
                    'display_name': request.form.get('project_name'),
                    'client_type': request.form.get('client_type'),
                    'client_phone': request.form.get('client_phone'),
                    'client_email': request.form.get('client_email'),
                    'client_address': request.form.get('client_address')
                }
                
                # Добавляем поля в зависимости от типа заказчика
                if request.form.get('client_type') == 'individual':
                    project_data.update({
                        'client_name': request.form.get('client_name'),
                        'client_passport': request.form.get('client_passport'),
                        'company_name': None,
                        'company_inn': None,
                        'company_ogrn': None
                    })
                else:
                    project_data.update({
                        'client_name': None,
                        'company_name': request.form.get('company_name'),
                        'company_inn': request.form.get('company_inn'),
                        'company_ogrn': request.form.get('company_ogrn')
                    })
                
                update_project(project_name, current_user.projects_folder, project_data)
                flash('Проект успешно обновлен!', 'success')
                return redirect(url_for('view_project', project_name=project_name))
                
            except Exception as e:
                flash(f'Ошибка при обновлении проекта: {str(e)}', 'error')
                return render_template('edit_project.html', project=project)
        
        return render_template('edit_project.html', project=project)

    @app.route('/project/<project_name>/delete', methods=['POST'])
    @login_required
    def delete_project(project_name):
        try:
            db_path = get_project_db_path(project_name, current_user.projects_folder)
            if db_path.exists():
                project_files_dir = Path(current_user.projects_folder) / project_name / 'files'
                if project_files_dir.exists():
                    import shutil
                    shutil.rmtree(str(project_files_dir))
                db_path.unlink()
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Проект не найден'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/project/<project_name>/duplicate', methods=['POST'])
    @login_required
    def duplicate_project(project_name):
        try:
            original = get_project_details(project_name, current_user.projects_folder)
            if not original:
                return jsonify({'success': False, 'error': 'Проект не найден'}), 404

            new_project_data = original.copy()
            new_project_data['project_name'] = f"Копия - {original['display_name']}"
            new_project_name = create_new_project(current_user.projects_folder, new_project_data)

            return jsonify({
                'success': True, 
                'project_name': new_project_name
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/rename_project', methods=['POST'])
    @login_required
    def rename_project():
        data = request.get_json()
        project_name = data.get('project_name')
        new_name = data.get('new_name')
        
        if not all([project_name, new_name]):
            return jsonify({'success': False, 'error': 'Missing required data'}), 400
        
        try:
            db_path = get_project_db_path(project_name, current_user.projects_folder)
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                c.execute("UPDATE project_data SET display_name = ? WHERE id = 1", (new_name,))
                conn.commit()
                conn.close()
                return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        
        return jsonify({'success': False, 'error': 'Project not found'}), 404

    # 3. Операции с объектами проекта
    @app.route('/project/<project_name>/objects', methods=['GET', 'POST'])
    @login_required
    def project_objects(project_name):
        if request.method == 'POST':
            try:
                object_name = request.form.get('object_name')
                if not object_name:
                    return jsonify({'success': False, 'error': 'Название объекта обязательно'}), 400
                    
                object_id = create_project_object(project_name, current_user.projects_folder, object_name)
                return jsonify({
                    'success': True,
                    'object': {
                        'id': object_id,
                        'name': object_name,
                        'status': 'active'
                    }
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
            
        objects = get_project_objects(project_name, current_user.projects_folder)
        return jsonify({'objects': objects})

    @app.route('/project/<project_name>/object/<int:object_id>/status', methods=['POST'])
    @login_required
    def update_object_status(project_name, object_id):
        try:
            status = request.form.get('status')
            if status not in ['active', 'completed']:
                return jsonify({'success': False, 'error': 'Неверный статус'}), 400
            
            conn = sqlite3.connect(str(get_project_db_path(project_name, current_user.projects_folder)))
            c = conn.cursor()
            c.execute("UPDATE project_objects SET status = ? WHERE id = ?", (status, object_id))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # 4. Операции с чатом и файлами
    @app.route('/project/<project_name>/object/<int:object_id>/chat', methods=['GET', 'POST'])
    @login_required
    def object_chat(project_name, object_id):
        if request.method == 'POST':
            try:
                content = request.form.get('message')
                if not content:
                    return jsonify({'success': False, 'error': 'Сообщение не может быть пустым'}), 400
                    
                message_type = request.form.get('type', 'user')
                add_chat_message(project_name, current_user.projects_folder, object_id, message_type, content)
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
            
        messages = get_chat_messages(project_name, current_user.projects_folder, object_id)
        return jsonify({'messages': messages})

    @app.route('/project/<project_name>/object/<int:object_id>/upload', methods=['POST'])
    @login_required
    def upload_file(project_name, object_id):
        try:
            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'Файл не найден'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'error': 'Файл не выбран'}), 400
            
            project_files_dir = Path(current_user.projects_folder) / project_name / 'files'
            project_files_dir.mkdir(parents=True, exist_ok=True)
            
            filename = file.filename
            file_path = project_files_dir / filename
            file.save(str(file_path))
            
            message = f"Загружен файл: {filename}"
            add_chat_message(project_name, current_user.projects_folder, object_id, 'file', message)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'message': message
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/project/<project_name>/status', methods=['POST'])
    @login_required
    def change_project_status(project_name):
        try:
            data = request.get_json()
            new_status = data.get('status')
            
            if new_status not in ['active', 'completed']:
                return jsonify({'success': False, 'error': 'Недопустимый статус'})
            
            user_folder = current_user.projects_folder  # Используем существующее свойство
            db_path = get_project_db_path(project_name, user_folder)
            
            if not db_path.exists():
                return jsonify({'success': False, 'error': 'Проект не найден'})
            
            conn = sqlite3.connect(str(db_path))
            c = conn.cursor()
            
            # Обновляем статус проекта
            c.execute("""
                UPDATE project_data 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = 1
            """, (new_status,))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    @app.template_filter('format_date')
    def format_date(date_str):
        """Форматирует дату в удобный для чтения вид"""
        if not date_str:
            return ''
        date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        return date.strftime('%d.%m.%Y %H:%M')

def create_project_object(project_name, user_folder, object_name):
    """Создание нового объекта в проекте"""
    conn = sqlite3.connect(str(get_project_db_path(project_name, user_folder)))
    c = conn.cursor()
    try:
        c.execute("INSERT INTO project_objects (name) VALUES (?)", (object_name,))
        object_id = c.lastrowid
        conn.commit()
        return object_id
    finally:
        conn.close()

def get_project_objects(project_name, user_folder):
    """Получение списка объектов проекта"""
    conn = sqlite3.connect(str(get_project_db_path(project_name, user_folder)))
    c = conn.cursor()
    try:
        c.execute("SELECT id, name, status, created_at FROM project_objects ORDER BY created_at DESC")
        columns = [description[0] for description in c.description]
        return [dict(zip(columns, row)) for row in c.fetchall()]
    finally:
        conn.close()

def add_chat_message(project_name, user_folder, object_id, message_type, content):
    """Добавление сообщения в чат объекта"""
    conn = sqlite3.connect(str(get_project_db_path(project_name, user_folder)))
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO chat_messages (object_id, message_type, content)
            VALUES (?, ?, ?)
        """, (object_id, message_type, content))
        conn.commit()
    finally:
        conn.close()

def get_chat_messages(project_name, user_folder, object_id):
    """Получение истории сообщений чата"""
    conn = sqlite3.connect(str(get_project_db_path(project_name, user_folder)))
    c = conn.cursor()
    try:
        c.execute("""
            SELECT id, message_type, content, created_at
            FROM chat_messages
            WHERE object_id = ?
            ORDER BY created_at ASC
        """, (object_id,))
        columns = [description[0] for description in c.description]
        return [dict(zip(columns, row)) for row in c.fetchall()]
    finally:
        conn.close()

def migrate_project_db(db_path):
    """Миграция базы данных проекта до актуальной версии"""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    try:
        # Проверяем существующие колонки
        c.execute("PRAGMA table_info(project_data)")
        columns = [column[1] for column in c.fetchall()]
        
        # Добавляем отсутствующие колонки
        if 'updated_at' not in columns:
            c.execute("ALTER TABLE project_data ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        if 'client_type' not in columns:
            c.execute("ALTER TABLE project_data ADD COLUMN client_type TEXT")
        if 'client_name' not in columns:
            c.execute("ALTER TABLE project_data ADD COLUMN client_name TEXT")
        if 'company_name' not in columns:
            c.execute("ALTER TABLE project_data ADD COLUMN company_name TEXT")
        if 'company_inn' not in columns:
            c.execute("ALTER TABLE project_data ADD COLUMN company_inn TEXT")
        
        conn.commit()
    finally:
        conn.close() 