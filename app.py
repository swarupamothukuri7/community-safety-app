from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
app = Flask(__name__)
app.secret_key = "community-safety-secret-key"

def get_db_connection():
    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending'
        )
    """)

    # Add user_id to an older reports table if it does not already exist
    columns = connection.execute("""
        PRAGMA table_info(reports)
    """).fetchall()

    column_names = [column["name"] for column in columns]

    if "user_id" not in column_names:
        connection.execute("""
            ALTER TABLE reports ADD COLUMN user_id INTEGER
        """)

    connection.commit()
    connection.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/report", methods=["GET", "POST"])
def report():

    # User must be logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        category = request.form["category"]
        location = request.form["location"]
        description = request.form["description"]

        user_id = session["user_id"]

        connection = get_db_connection()

        connection.execute("""
            INSERT INTO reports
            (user_id, category, location, description)
            VALUES (?, ?, ?, ?)
        """, (user_id, category, location, description))

        connection.commit()
        connection.close()

        return """
        <h2>Report submitted successfully!</h2>
        <p>Your safety issue has been recorded.</p>
        <a href="/">Go back to Home</a>
        """

    return render_template("report.html")


@app.route("/reports")
def reports():

    connection = get_db_connection()

    reports = connection.execute("""
        SELECT * FROM reports
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    return render_template("reports.html", reports=reports)

@app.route("/my-reports")
def my_reports():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    reports = connection.execute("""
        SELECT * FROM reports
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    connection.close()

    return render_template("my_reports.html", reports=reports)

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        connection = get_db_connection()

        try:
            connection.execute("""
                INSERT INTO users (name, email, password)
                VALUES (?, ?, ?)
            """, (name, email, hashed_password))

            connection.commit()

        except sqlite3.IntegrityError:
            connection.close()
            return """
            <h2>Email already registered!</h2>
            <p>Please use a different email address.</p>
            <a href="/register">Go back</a>
            """

        connection.close()

        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_db_connection()

        user = connection.execute("""
            SELECT * FROM users
            WHERE email = ?
        """, (email,)).fetchone()

        connection.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect(url_for("home"))

        return """
        <h2>Invalid email or password</h2>
        <p>Please check your login details.</p>
        <a href="/login">Try Again</a>
        """

    return render_template("login.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        if email == "admin@community.com" and password == "admin123":

            session["admin_logged_in"] = True

            return redirect(url_for("admin_dashboard"))

        return """
        <h2>Invalid Admin Login</h2>
        <p>Please check the admin email and password.</p>
        <a href="/admin/login">Try Again</a>
        """

    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    connection = get_db_connection()

    reports = connection.execute("""
        SELECT reports.*, users.name, users.email
        FROM reports
        LEFT JOIN users ON reports.user_id = users.id
        ORDER BY reports.id DESC
    """).fetchall()

    connection.close()

    return render_template("admin_dashboard.html", reports=reports)

@app.route("/admin/update/<int:report_id>", methods=["POST"])
def update_report_status(report_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    status = request.form["status"]

    connection = get_db_connection()

    connection.execute("""
        UPDATE reports
        SET status = ?
        WHERE id = ?
    """, (status, report_id))

    connection.commit()
    connection.close()

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_logged_in", None)

    return redirect(url_for("admin_login"))

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))

if __name__ == "__main__":
    create_database()
    app.run(debug=True)