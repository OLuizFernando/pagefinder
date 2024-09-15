import os

from cs50 import SQL
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, send_from_directory, session
from helpers import login_required, format_number
from werkzeug.security import check_password_hash, generate_password_hash

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.jinja_env.filters['format_number'] = format_number

# Configure CS50 Library to use SQLite database
db = SQL(os.getenv("POSTGRESQL_URL"))


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    if session:
        return redirect("/readings")

    else:
        return redirect("/login")


@app.route("/add_book", methods=["GET", "POST"])
@login_required
def add_book():
    if request.method == "POST":
        title = request.form.get("title")
        author = request.form.get("author")
        action = request.form.get("action")
        total_pages = request.form.get("total_pages")
        pages_read = request.form.get("pages_read")
        purchase_url = request.form.get("purchase_url")
        finish_date = request.form.get("finish_date")

        if not action:
            flash("You must select an action.")
            return render_template("add_book.html")

        if not title or not author or (action == "reading" and not total_pages):
            flash("You must fill in all fields.")
            return render_template("add_book.html")

        if not pages_read:
            pages_read = 0

        book_id = db.execute("SELECT book_id FROM books WHERE title ILIKE ?", f"%{title}%")

        author_id = db.execute("SELECT author_id FROM authors WHERE name ILIKE ?", f"%{author}%")

        if not book_id:
            flash("Book not found. Try to register a new book to our database.")
            return render_template("add_book.html")

        if not author_id:
            flash("Author not found. Try to register a new author to our database.")
            return render_template("add_book.html")

        try:
            authorship_id = db.execute(
                "SELECT authorship_id FROM authorships WHERE book_id = ? AND author_id = ?",book_id[0]["book_id"], author_id[0]["author_id"]
            )[0]["authorship_id"]

        except:
            flash("Book and/or author not found. Try to register a new book/author to our database.")
            return render_template("add_book.html", book_titles=book_titles, author_names=author_names)

        if action == "reading":
            db.execute(
                "INSERT INTO readings (user_id, authorship_id, total_pages, pages_read) VALUES (?, ?, ?, ?)",
                session["user_id"], authorship_id, total_pages, pages_read
            )

            # removes book from user's wish list if it's there
            user_wish_list = db.execute("SELECT * FROM wish_lists WHERE user_id = ?", session["user_id"])
            if any(dict["authorship_id"] == authorship_id for dict in user_wish_list):
                db.execute("DELETE FROM wish_lists WHERE user_id = ? AND authorship_id = ?", session["user_id"], authorship_id)

            return redirect("/readings")

        elif action == "wish_list":
            db.execute(
                "INSERT INTO wish_lists (user_id, authorship_id, purchase_url) VALUES (?, ?, ?)",
                session["user_id"], authorship_id, purchase_url
            )
            return redirect("/wish_list")

        elif action == "finished":
            if finish_date:
                finish_year = finish_date[0:4]
                finish_month = finish_date[5:7]
                finish_day = finish_date[8:]

                db.execute(
                    "INSERT INTO finished (user_id, authorship_id, finish_year, finish_month, finish_day) VALUES (?, ?, ?, ?, ?)",
                    session["user_id"], authorship_id, finish_year, finish_month, finish_day
                )
            else:
                db.execute(
                    "INSERT INTO finished (user_id, authorship_id) VALUES (?, ?)",
                    session["user_id"], authorship_id
                )

            # removes book from user's readings if it's there
            user_readings = db.execute("SELECT * FROM readings WHERE user_id = ?", session["user_id"])
            if any(dict["authorship_id"] == authorship_id for dict in user_readings):
                db.execute("DELETE FROM readings WHERE user_id = ? AND authorship_id = ?", session["user_id"], authorship_id)

            return redirect("/finished")

    else:
        book_titles = db.execute("SELECT title FROM books")
        author_names = db.execute("SELECT name FROM authors")

        return render_template("add_book.html", book_titles=book_titles, author_names=author_names)


@app.route("/book_info", methods=["POST"])
@login_required
def book_info():
    query = '''
    SELECT
        books.title,
        books.year,
        authors.name AS author,
        authors.birth,
        authorships.authorship_id
    FROM
        books
    INNER JOIN
        authorships ON books.book_id = authorships.book_id
    INNER JOIN
        authors ON authorships.author_id = authors.author_id
    WHERE authorships.authorship_id = ?
    '''
    authorship_id = request.form.get("book_info")
    book_info = db.execute(query, authorship_id)[0]

    return render_template("book_info.html", book_info=book_info)


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        current_password_hash = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])[0]["hash"]

        new_password = request.form.get("new_password")
        confirm_new_password = request.form.get("confirm_new_password")

        if not current_password or not new_password or not confirm_new_password:
            flash("You must fill in all fields.")
            return render_template("change_password.html")

        if not check_password_hash(current_password_hash, current_password):
            flash("Invalid current password.")
            return render_template("change_password.html")

        if new_password != confirm_new_password:
            flash("\"New password confirmation\" doesn't match.")
            return render_template("change_password.html")

        new_password_hash = generate_password_hash(new_password)

        db.execute(
            "UPDATE users SET hash = ? WHERE id = ?", new_password_hash, session["user_id"]
        )

        return redirect("/")

    else:
        username = db.execute(
            "SELECT username FROM users WHERE id = ?", session["user_id"]
        )[0]["username"]

        return render_template("change_password.html", username=username)


@app.route("/delete_account", methods=["GET", "POST"])
@login_required
def delete_account():
    username = db.execute(
        "SELECT username FROM users WHERE id = ?", session["user_id"]
    )[0]["username"]

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation:
            flash("You must fill in all fields.")
            return render_template("delete_account.html", username=username)

        user_info = db.execute("SELECT username, hash FROM users WHERE id = ?", session["user_id"])[0]

        if username != user_info["username"] or not check_password_hash(
            user_info["hash"], password
        ):
            flash("Invalid username and/or password.")
            return render_template("delete_account.html", username=username)

        if confirmation.lower().strip() != "delete my account":
            flash("Confirmation doensn't match.")
            return render_template("delete_account.html", username=username)

        db.execute("DELETE FROM readings WHERE user_id = ?", session["user_id"])
        db.execute("DELETE FROM wish_lists WHERE user_id = ?", session["user_id"])
        db.execute("DELETE FROM finished WHERE user_id = ?", session["user_id"])
        db.execute("DELETE FROM users WHERE id = ?", session["user_id"])
        session.clear()

        return redirect("/")

    else:
        return render_template("delete_account.html", username=username)


@app.route("/delete_from_user_lists", methods=["POST"])
@login_required
def delete_from_user_lists():
    authorship_id = request.form.get("delete")
    db.execute("DELETE FROM readings WHERE user_id = ? AND authorship_id = ?", session["user_id"], authorship_id)
    db.execute("DELETE FROM wish_lists WHERE user_id = ? AND authorship_id = ?", session["user_id"], authorship_id)
    db.execute("DELETE FROM finished WHERE user_id = ? AND authorship_id = ?", session["user_id"], authorship_id)
    return redirect("/")


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


@app.route("/finished")
@login_required
def finished():
    query = '''
    SELECT
        books.title,
        authors.name AS author,
        authorships.authorship_id,
        finished.finish_year,
        finished.finish_month,
        finished.finish_day
    FROM
        books
    INNER JOIN
        authorships ON books.book_id = authorships.book_id
    INNER JOIN
        finished ON finished.authorship_id = authorships.authorship_id
    INNER JOIN
        authors ON authorships.author_id = authors.author_id
    WHERE authorships.authorship_id IN (
        SELECT authorship_id FROM finished WHERE user_id = ?
    )
    AND finished.user_id = ?
    '''
    user_finished = db.execute(query, session["user_id"], session["user_id"])
    user_finished.reverse()

    return render_template("finished.html", user_finished=user_finished)


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("You must fill in all fields.")
            return render_template("login.html")

        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", username
        )

        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], password
        ):
            flash("Invalid username and/or password.")
            return render_template("login.html")

        session["user_id"] = rows[0]["id"]

        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/options", methods=["GET", "POST"])
@login_required
def options():
    if request.method == "POST":
        if request.form["action"] == "change_password":
            return redirect("/change_password")

        if request.form["action"] == "delete_account":
            return redirect("/delete_account")

    else:
        username = db.execute(
            "SELECT username FROM users WHERE id = ?", session["user_id"]
        )[0]["username"]

        return render_template("options.html", username=username)


@app.route("/readings")
@login_required
def reading():
    query = '''
    SELECT
        authorships.authorship_id,
        books.title,
        authors.name AS author,
        readings.reading_id,
        readings.total_pages,
        readings.pages_read
    FROM
        books
    INNER JOIN
        authorships ON books.book_id = authorships.book_id
    INNER JOIN
        readings ON readings.authorship_id = authorships.authorship_id
    INNER JOIN
        authors ON authorships.author_id = authors.author_id
    WHERE authorships.authorship_id IN (
        SELECT authorship_id FROM readings WHERE user_id = ?
    )
    AND readings.user_id = ?
    '''
    user_readings = db.execute(query, session["user_id"], session["user_id"])
    user_readings.reverse()

    return render_template("readings.html", user_readings=user_readings)


@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not username or not password or not confirm_password:
            flash("You must fill in all fields.")
            return render_template("register.html")

        if password != confirm_password:
            flash("Confirm you password correctly.")
            return render_template("register.html")

        username_already_taken = db.execute(
            "SELECT 1 FROM users WHERE username = ?", username
        )

        if username_already_taken:
            flash("Username already taken. Please choose another.")
            return render_template("register.html")

        password_hash = generate_password_hash(password)

        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)", username, password_hash
        )

        return render_template("registered.html")

    else:
        return render_template("register.html")


@app.route("/register_author", methods=["GET", "POST"])
@login_required
def register_author():
    if request.method == "POST":
        name = request.form.get("name").strip()
        birth = request.form.get("birth").strip()

        if not name or not birth:
            flash("You must fill in all fields.")
            return render_template("register_author.html")

        if not birth.isnumeric():
            flash("Invalid author's birth year.")
            return render_template("register_author.html")

        db.execute("INSERT INTO authors (name, birth) VALUES (?, ?)", name, birth)

        return render_template("author_registered.html", name=name)

    else:
        return render_template("register_author.html")


@app.route("/register_book", methods=["GET", "POST"])
@login_required
def register_book():
    if request.method == "POST":
        title = request.form.get("title").strip()
        author = request.form.get("author").strip()
        year = request.form.get("year").strip()

        if not title or not author or not year:
            flash("You must fill in all fields.")
            return render_template("register_book.html")

        if not year.isnumeric():
            flash("Invalid publication year.")
            return render_template("register_book.html")

        author_id = db.execute("SELECT author_id FROM authors WHERE name ILIKE ?", f"%{author}%")

        if not author_id:
            flash("Author not found. Try to register a new author to our database.")
            return render_template("register_book.html")

        try:
            db.execute("INSERT INTO books (title, year) VALUES (?, ?)", title, year)

            book_id = db.execute("SELECT book_id FROM books WHERE title ILIKE ? AND year = ?", f"%{title}%", year)

            db.execute("INSERT INTO authorships (author_id, book_id) VALUES (?, ?)", author_id[0]["author_id"], book_id[0]["book_id"])

        except:
            flash("Unexpected error. Try again later.")
            return render_template("register_book.html")

        return render_template("book_registered.html", title=title)

    else:
        return render_template("register_book.html")


@app.route("/tester_login")
def tester_login():
    session.clear()
    session["user_id"] = 1

    return redirect("/")


@app.route("/update_reading", methods=["POST"])
@login_required
def update_reading():
    if request.form.get("update_reading"):
        reading_id = request.form.get("update_reading")
        pages_read = request.form.get("pages_read")

        if not pages_read:
            flash("You must fill in all fields.")
            return render_template("update_reading.html", reading_id=reading_id)

        total_pages = db.execute("SELECT total_pages FROM readings WHERE user_id = ? AND reading_id = ?", session["user_id"], reading_id)[0]["total_pages"]

        if int(pages_read) > int(total_pages):
            flash("Number of pages read must be less than or equal to the total number of pages")
            return render_template("update_reading.html", reading_id=reading_id)

        if int(pages_read) < int(total_pages):
            db.execute("UPDATE readings SET pages_read = ? WHERE reading_id = ? AND user_id = ?", pages_read, reading_id, session["user_id"])

        else:
            authorship_id = db.execute(
                "SELECT authorship_id FROM readings WHERE reading_id = ? AND user_id = ?",
                reading_id, session["user_id"]
            )[0]["authorship_id"]

            now = datetime.now()
            year = now.year
            month = now.month
            day = now.day

            db.execute(
                "INSERT INTO finished (user_id, authorship_id, finish_year, finish_month, finish_day) VALUES (?, ?, ?, ?, ?)",
                session["user_id"], authorship_id, year, month, day
            )

            db.execute("DELETE FROM readings WHERE reading_id = ? AND user_id = ?", reading_id, session["user_id"])

        return redirect("/readings")


    if request.form.get("goto_update_reading"):
        reading_id = request.form.get("goto_update_reading")
        return render_template("update_reading.html", reading_id=reading_id)


@app.route("/wish_list")
@login_required
def wish_list():
    query = '''
    SELECT
        books.title,
        authors.name AS author,
        authorships.authorship_id,
        wish_lists.purchase_url
    FROM
        books
    INNER JOIN
        authorships ON books.book_id = authorships.book_id
    INNER JOIN
        wish_lists ON wish_lists.authorship_id = authorships.authorship_id
    INNER JOIN
        authors ON authorships.author_id = authors.author_id
    WHERE authorships.authorship_id IN (
        SELECT authorship_id FROM wish_lists WHERE user_id = ?
    )
    AND wish_lists.user_id = ?
    '''
    user_wish_list = db.execute(query, session["user_id"], session["user_id"])
    user_wish_list.reverse()

    return render_template("wish_list.html", user_wish_list=user_wish_list)


if __name__ == '__main__':
    app.run(debug=True)