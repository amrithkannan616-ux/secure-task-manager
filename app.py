from flask import Flask, render_template_string, request, redirect, url_for, session
import bcrypt
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

load_dotenv()
import sqlite3

app = Flask(__name__)
app.secret_key = "securekey"

rds_password = os.getenv("RDS_PASSWORD")

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://admin:{rds_password}@secure-task-db.cb0aim46i3hq.ap-south-1.rds.amazonaws.com/taskdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        user_id INTEGER
    )
    ''')

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute("SELECT id, role FROM users WHERE username=?", (session['user'],))
    user = c.fetchone()

    if not user:
        session.pop('user', None)
        return redirect(url_for('login'))

    c.execute("SELECT * FROM tasks WHERE user_id=?", (user[0],))
    tasks = c.fetchall()

    conn.close()

    return render_template_string("""
    <h1>Secure Task Manager</h1>
    <h3>Welcome {{session['user']}}</h3>
    <p>Role: {{role}}</p>

    {% if role == 'admin' %}
        <a href="/admin">Admin Dashboard</a><br><br>
    {% endif %}

    <form method="POST" action="/add">
        <input type="text" name="task" placeholder="Enter task" required>
        <button type="submit">Add Task</button>
    </form>

    <br>

    {% for task in tasks %}
        <p>
            {{task[1]}}
            <a href="/edit/{{task[0]}}">Edit</a>
            <a href="/delete/{{task[0]}}">Delete</a>
        </p>
    {% endfor %}

    <br>
    <a href="/logout">Logout</a>
    """, tasks=tasks, role=user[1])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        hashed_password = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        role = "admin" if username == "admin" else "user"

        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()

        try:
            c.execute(
                "INSERT INTO users(username,password,role) VALUES (?,?,?)",
                (username, hashed_password, role)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "User already exists"

        conn.close()
        return redirect(url_for('login'))

    return """
    <h1>Register</h1>
    <form method="POST">
        <input type="text" name="username" placeholder="Username" required><br><br>
        <input type="password" name="password" placeholder="Password" required><br><br>
        <button type="submit">Register</button>
    </form>
    <br>
    <a href="/login">Login</a>
    """

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()

        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            session['user'] = username
            return redirect(url_for('home'))

        return "Invalid credentials"

    return """
    <h1>Login</h1>
    <form method="POST">
        <input type="text" name="username" placeholder="Username" required><br><br>
        <input type="password" name="password" placeholder="Password" required><br><br>
        <button type="submit">Login</button>
    </form>
    <br>
    <a href="/register">Register</a>
    """

@app.route('/add', methods=['POST'])
def add():
    if 'user' not in session:
        return redirect(url_for('login'))

    task = request.form['task']

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute("SELECT id FROM users WHERE username=?", (session['user'],))
    user = c.fetchone()

    c.execute(
        "INSERT INTO tasks(title,user_id) VALUES (?,?)",
        (task, user[0])
    )

    conn.commit()
    conn.close()

    return redirect(url_for('home'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    if request.method == 'POST':
        new_task = request.form['task']

        c.execute(
            "UPDATE tasks SET title=? WHERE id=?",
            (new_task, id)
        )

        conn.commit()
        conn.close()

        return redirect(url_for('home'))

    c.execute("SELECT * FROM tasks WHERE id=?", (id,))
    task = c.fetchone()

    conn.close()

    return render_template_string("""
    <h1>Edit Task</h1>
    <form method="POST">
        <input type="text" name="task" value="{{task[1]}}" required>
        <button type="submit">Update</button>
    </form>
    """, task=task)

@app.route('/delete/<int:id>')
def delete(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute("DELETE FROM tasks WHERE id=?", (id,))
    conn.commit()

    conn.close()

    return redirect(url_for('home'))

@app.route('/admin')
def admin():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute("SELECT role FROM users WHERE username=?", (session['user'],))
    role = c.fetchone()

    if not role or role[0] != 'admin':
        conn.close()
        return "Access Denied"

    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = c.fetchone()[0]

    c.execute("SELECT username, role FROM users")
    users = c.fetchall()

    c.execute("""
    SELECT tasks.id, tasks.title, users.username
    FROM tasks
    JOIN users ON tasks.user_id = users.id
    """)

    all_tasks = c.fetchall()

    conn.close()

    return render_template_string("""
    <h1>Admin Dashboard</h1>

    <h3>Total Users: {{total_users}}</h3>
    <h3>Total Tasks: {{total_tasks}}</h3>

    <h2>Users</h2>
    {% for user in users %}
        <p>{{user[0]}} - {{user[1]}}</p>
    {% endfor %}

    <hr>

    <h2>All Tasks</h2>
    {% for task in all_tasks %}
        <p>
            {{task[1]}} - by {{task[2]}}
            <a href="/admin/delete/{{task[0]}}">Delete</a>
        </p>
    {% endfor %}

    <br>
    <a href="/">Back</a>
    """,
    total_users=total_users,
    total_tasks=total_tasks,
    users=users,
    all_tasks=all_tasks)

@app.route('/admin/delete/<int:id>')
def admin_delete(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute("SELECT role FROM users WHERE username=?", (session['user'],))
    role = c.fetchone()

    if not role or role[0] != 'admin':
        conn.close()
        return "Access Denied"

    c.execute("DELETE FROM tasks WHERE id=?", (id,))
    conn.commit()

    conn.close()

    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
