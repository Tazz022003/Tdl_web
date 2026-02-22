
from flask import Flask
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import render_template, request, redirect, url_for
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

@app.route("/dashboard")
@login_required
def dashboard():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id=? ORDER BY due_date, due_time",
        (current_user.id,)
    ).fetchall()
    conn.close()
    return render_template("dashboard.html", tasks=tasks)

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