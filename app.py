from flask import Flask, render_template, request, jsonify
import sqlite3
from pathlib import Path
import os

app = Flask(__name__)

# Папка для хранения баз данных проектов
PROJECTS_DIR = Path("projects")
PROJECTS_DIR.mkdir(exist_ok=True)

# Последовательность вопросов
QUESTIONS = [
    "Введите имя проекта",
    "Введите расстояние до объекта (км)",
    "Введите стоимость километра (руб)"
]

def get_project_db_path(project_name):
    """Получить путь к базе данных проекта"""
    return PROJECTS_DIR / f"{project_name}.db"

def init_project_db(project_name):
    """Инициализация базы данных для проекта"""
    db_path = get_project_db_path(project_name)
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

def get_all_projects():
    """Получить данные всех проектов"""
    projects = []
    if not PROJECTS_DIR.exists():
        return projects
        
    for db_file in PROJECTS_DIR.glob("*.db"):
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
                    'display_name': row[1] or row[0],  # Если display_name пустой, используем project_name
                    'distance': row[2],
                    'cost_per_km': row[3],
                    'total_cost': row[4]
                })
            conn.close()
        except sqlite3.Error:
            continue
    return projects

def update_project_data(project_name, field, value):
    """Обновить данные проекта"""
    db_path = get_project_db_path(project_name)
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    try:
        # Обновляем указанное поле
        c.execute(f"UPDATE project_data SET {field} = ? WHERE id = 1", (value,))
        
        # Если обновляем distance или cost_per_km, пересчитываем total_cost
        if field in ['distance', 'cost_per_km']:
            c.execute("SELECT distance, cost_per_km FROM project_data WHERE id = 1")
            distance, cost_per_km = c.fetchone()
            
            if distance is not None and cost_per_km is not None:
                total_cost = float(distance) * float(cost_per_km)
                c.execute("UPDATE project_data SET total_cost = ? WHERE id = 1", (total_cost,))
        
        conn.commit()
        
        # Возвращаем обновленные данные
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

@app.route('/')
def index():
    projects = get_all_projects()
    return render_template('index.html', current_question=QUESTIONS[0], projects=projects)

@app.route('/submit', methods=['POST'])
def submit():
    answer = request.form['input_field']
    current_question = request.form['current_question']
    
    try:
        # Обработка имени проекта
        if current_question == QUESTIONS[0]:
            # Создаем безопасное имя файла для базы данных
            db_name = answer.lower().replace(' ', '_')
            
            # Проверяем, не существует ли уже такой проект
            db_path = get_project_db_path(db_name)
            if db_path.exists():
                return render_template('index.html',
                                    result=f"Проект с таким именем уже существует",
                                    current_question=QUESTIONS[0],
                                    projects=get_all_projects())
            
            # Создаем новую базу данных для проекта
            init_project_db(db_name)
            
            # Вставляем начальные данные проекта
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
            
        # Обработка расстояния
        elif current_question == QUESTIONS[1]:
            # Получаем последний созданный проект
            latest_db = max(PROJECTS_DIR.glob("*.db"), key=os.path.getctime)
            project_name = latest_db.stem
            
            distance = float(answer)
            update_project_data(project_name, 'distance', distance)
            next_question = QUESTIONS[2]
            
        # Обработка стоимости за километр
        elif current_question == QUESTIONS[2]:
            latest_db = max(PROJECTS_DIR.glob("*.db"), key=os.path.getctime)
            project_name = latest_db.stem
            
            cost_per_km = float(answer)
            update_project_data(project_name, 'cost_per_km', cost_per_km)
            
            # Получаем обновленные данные проекта для отображения результата
            conn = sqlite3.connect(str(latest_db))
            c = conn.cursor()
            c.execute("""
                SELECT display_name, total_cost 
                FROM project_data 
                WHERE id = 1
            """)
            result = c.fetchone()
            conn.close()
            
            next_question = QUESTIONS[0]
            return render_template('index.html',
                                result=f"Стоимость проекта '{result[0]}' составит {result[1]} руб.",
                                current_question=next_question,
                                projects=get_all_projects())
    
    except (ValueError, sqlite3.Error) as e:
        return render_template('index.html',
                             result=f"Ошибка: Проверьте введенные данные",
                             current_question=current_question,
                             projects=get_all_projects())
    
    return render_template('index.html',
                         current_question=next_question,
                         projects=get_all_projects())

@app.route('/delete_project', methods=['POST'])
def delete_project():
    data = request.get_json()
    project_name = data.get('project_name')
    if project_name:
        try:
            db_path = get_project_db_path(project_name)
            if db_path.exists():
                db_path.unlink()  # Удаляем файл базы данных
                return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': False, 'error': 'Project name not provided'}), 400

@app.route('/update_project', methods=['POST'])
def update_project():
    data = request.get_json()
    project_name = data.get('project_name')
    field = data.get('field')
    value = data.get('value')
    
    if not all([project_name, field, value]):
        return jsonify({'success': False, 'error': 'Missing required data'}), 400
    
    try:
        # Преобразуем значение в число для числовых полей
        if field in ['distance', 'cost_per_km']:
            value = float(value)
        
        # Получаем обновленные данные
        updated_data = update_project_data(project_name, field, value)
        
        # Возвращаем обновленные данные клиенту
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
        db_path = get_project_db_path(project_name)
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

if __name__ == '__main__':
    app.run(debug=True)