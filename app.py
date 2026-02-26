
from flask import Flask
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import sqlite3
#from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
#from flask import render_template, request, redirect, url_for
from datetime import datetime
#from flask import request
import sqlite3


app = Flask(__name__)
app.secret_key = "secret"


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id):
        self.id = id

# 5️ User Loader
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            login_user(User(user["id"]))
            return redirect(url_for("dashboard"))

    return render_template("login.html")

@app.route("/done/<int:task_id>")
@login_required
def done(task_id):
    conn = sqlite3.connect("database.db")
    conn.execute("UPDATE tasks SET status='Done' WHERE id=? AND user_id=?", (task_id, current_user.id))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/undo/<int:task_id>")
@login_required
def undo(task_id):
    conn = sqlite3.connect("database.db")
    conn.execute(
        "UPDATE tasks SET status='Pending' WHERE id=? AND user_id=?",
        (task_id, current_user.id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

@app.route("/delete/<int:task_id>")
@login_required
def delete(task_id):
    conn = sqlite3.connect("database.db")

    conn.execute("""
        DELETE FROM tasks
        WHERE id=? AND user_id=?
    """, (task_id, current_user.id))

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

@app.route("/edit/<int:task_id>", methods=["GET", "POST"])
@login_required
def edit(task_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    if request.method == "POST":
        name = request.form["name"]
        category = request.form["category"]
        priority = request.form["priority"]
        due_date = request.form["due_date"]
        due_time = request.form["due_time"]

        conn.execute("""
            UPDATE tasks
            SET name=?, category=?, priority=?, due_date=?, due_time=?
            WHERE id=? AND user_id=?
        """, (name, category, priority, due_date, due_time, task_id, current_user.id))

        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))

    task = conn.execute("""
        SELECT * FROM tasks
        WHERE id=? AND user_id=?
    """, (task_id, current_user.id)).fetchone()

    conn.close()
    return render_template("edit_task.html", task=task)


@app.route("/dashboard")
@login_required
def dashboard():
    search = request.args.get("search")
    category = request.args.get("category")

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM tasks WHERE user_id=?"
    params = [current_user.id]

    if search:
        query += " AND name LIKE ?"
        params.append(f"%{search}%")

    if category and category != "All":
        query += " AND category=?"
        params.append(category)

    # Sort by nearest due date
    query += " ORDER BY due_date ASC, due_time ASC"

    tasks = conn.execute(query, params).fetchall()
    conn.close()

    # Separate Pending and Done
    pending_tasks = [t for t in tasks if t["status"] == "Pending"]
    done_tasks = [t for t in tasks if t["status"] == "Done"]

    total = len(tasks)
    pending = len(pending_tasks)
    done = len(done_tasks)

    return render_template(
        "dashboard.html",
        pending_tasks=pending_tasks,
        done_tasks=done_tasks,
        total=total,
        done=done,
        pending=pending,
        overdue=0
    )
   
   
    

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/add_task", methods=["GET", "POST"])
@login_required
def add_task():
    if request.method == "POST":
        name = request.form["name"]
        category = request.form["category"]
        priority = request.form["priority"]
        due_date = request.form["due_date"]
        due_time = request.form["due_time"]

        conn = sqlite3.connect("database.db")
        conn.execute("""
            INSERT INTO tasks (user_id, name, category, priority, due_date, due_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (current_user.id, name, category, priority, due_date, due_time))
        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("add_task.html")

@app.route("/overdue")
@login_required
def overdue():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    tasks = conn.execute("""
        SELECT * FROM tasks
        WHERE user_id=? AND status='Pending'
    """, (current_user.id,)).fetchall()

    conn.close()

    overdue_tasks = []
    now = datetime.now()

    for task in tasks:
        task_datetime = datetime.strptime(
            task["due_date"] + " " + task["due_time"],
            "%Y-%m-%d %H:%M"
        )

        if task_datetime < now:
            overdue_tasks.append(task)

    return render_template("overdue.html", tasks=overdue_tasks)

@app.route("/analytics")
@login_required
def analytics():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    tasks = conn.execute("""
        SELECT * FROM tasks
        WHERE user_id=?
    """, (current_user.id,)).fetchall()

    conn.close()

    total = len(tasks)
    done = len([t for t in tasks if t["status"] == "Done"])
    pending = len([t for t in tasks if t["status"] == "Pending"])

    # Count overdue
    overdue = 0
    now = datetime.now()

    for task in tasks:
        if task["status"] == "Pending":
            task_datetime = datetime.strptime(
                task["due_date"] + " " + task["due_time"],
                "%Y-%m-%d %H:%M"
            )
            if task_datetime < now:
                overdue += 1

    return render_template(
        "analytics.html",
        total=total,
        done=done,
        pending=pending,
        overdue=overdue
    )
        
def create_tables():
    conn = sqlite3.connect("database.db")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        category TEXT,
        priority TEXT,
        due_date TEXT,
        due_time TEXT,
        status TEXT DEFAULT 'Pending'
    )
    """)

    conn.commit()
    conn.close()

create_tables()

@app.route("/")
def home():
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)