from flask import render_template, request, jsonify, redirect, url_for
import sqlite3
from pathlib import Path
import os
from flask_login import login_required, current_user

# Папка для хранения баз данных проектов
PROJECTS_DIR = Path("projects")
PROJECTS_DIR.mkdir(exist_ok=True)

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
            c.execute("""
                SELECT project_name, display_name, distance, cost_per_km, total_cost 
                FROM project_data
                WHERE id = 1
            """)
            row = c.fetchone()
            if row:
                projects.append({
                    'project_name': row[0],
                    'display_name': row[1] or row[0],
                    'distance': row[2],
                    'cost_per_km': row[3],
                    'total_cost': row[4]
                })
            conn.close()
        except sqlite3.Error:
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS project_data
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         project_name TEXT,
         display_name TEXT,
         distance REAL,
         cost_per_km REAL,
         total_cost REAL)
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

def init_routes(app):
    """Инициализация всех маршрутов"""
    
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

    @app.route('/submit', methods=['POST'])
    @login_required
    def submit():
        answer = request.form['input_field']
        current_question = request.form['current_question']
        
        try:
            if current_question == QUESTIONS[0]:
                db_name = answer.lower().replace(' ', '_')
                db_path = get_project_db_path(db_name, current_user.projects_folder)
                
                if db_path.exists():
                    return render_template('dashboard.html',
                                        result=f"Проект с таким именем уже существует",
                                        current_question=QUESTIONS[0],
                                        projects=get_user_projects(current_user.projects_folder))
                
                init_project_db(db_name, current_user.projects_folder)
                
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                c.execute("""
                    INSERT INTO project_data 
                    (project_name, display_name, distance, cost_per_km, total_cost) 
                    VALUES (?, ?, NULL, NULL, NULL)
                """, (db_name, answer))
                conn.commit()
                conn.close()
                
                next_question = QUESTIONS[1]
                
            elif current_question == QUESTIONS[1]:
                latest_db = max(Path(current_user.projects_folder).glob("*.db"), 
                              key=os.path.getctime)
                project_name = latest_db.stem
                
                distance = float(answer)
                update_project_data(project_name, 'distance', distance, 
                                  current_user.projects_folder)
                next_question = QUESTIONS[2]
                
            elif current_question == QUESTIONS[2]:
                latest_db = max(Path(current_user.projects_folder).glob("*.db"), 
                              key=os.path.getctime)
                project_name = latest_db.stem
                
                cost_per_km = float(answer)
                updated_data = update_project_data(project_name, 'cost_per_km', 
                                                 cost_per_km, current_user.projects_folder)
                
                next_question = QUESTIONS[0]
                return render_template('dashboard.html',
                                    result=f"Стоимость проекта '{updated_data['display_name']}' составит {updated_data['total_cost']} руб.",
                                    current_question=next_question,
                                    projects=get_user_projects(current_user.projects_folder))
        
        except (ValueError, sqlite3.Error) as e:
            return render_template('dashboard.html',
                                result=f"Ошибка: Проверьте введенные данные",
                                current_question=current_question,
                                projects=get_user_projects(current_user.projects_folder))
        
        return render_template('dashboard.html',
                            current_question=next_question,
                            projects=get_user_projects(current_user.projects_folder))

    @app.route('/delete_project', methods=['POST'])
    @login_required
    def delete_project():
        data = request.get_json()
        project_name = data.get('project_name')
        if project_name:
            try:
                db_path = get_project_db_path(project_name, current_user.projects_folder)
                if db_path.exists():
                    db_path.unlink()
                    return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        return jsonify({'success': False, 'error': 'Project name not provided'}), 400

    @app.route('/update_project', methods=['POST'])
    @login_required
    def update_project():
        data = request.get_json()
        project_name = data.get('project_name')
        field = data.get('field')
        value = data.get('value')
        
        if not all([project_name, field, value]):
            return jsonify({'success': False, 'error': 'Missing required data'}), 400
        
        try:
            if field in ['distance', 'cost_per_km']:
                value = float(value)
            
            updated_data = update_project_data(project_name, field, value, 
                                             current_user.projects_folder)
            
            return jsonify({
                'success': True,
                'data': updated_data
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/rename_project', methods=['POST'])
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