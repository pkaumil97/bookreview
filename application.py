import os
import requests
from flask import Flask, session, render_template, request, flash, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login/", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        verification = db.execute("SELECT * FROM users WHERE username=:username", {"username": username}).fetchone()
        if verification is None:
            flash("Username does not exist")
            flash("Don't have an account, register for Free!")
        elif verification is not None and verification["password"] == password:
            flash("Login successfully")
            session['username'] = username
            return redirect(url_for('index'))
        elif verification is not None and verification["password"] != password:
            flash("wrong password.")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout/', methods=['GET', 'POST'])
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route("/register/", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == "" or password == "":
            flash("Please, fill all the fields")
            return render_template('register.html')
        else:
            untaken_username = db.execute("SELECT * FROM users WHERE username=:username",
                                          {"username": username}).fetchone()

            if untaken_username is None:

                db.execute("INSERT INTO users(username, password) VALUES (:username, :password)", {"username": username,
                                                                                                   "password": password}
                           )
                db.commit()
                flash('successfully registered, please login')
                return redirect(url_for('login'))
            else:
                flash("username already exists")
                return render_template("register.html")
    return render_template('register.html')


@app.route('/search/', methods=['GET', 'POST'])
def search():
    books = []
    if request.method == "POST":
        searchType = request.form.get('searchType')
        searchContent = request.form.get('searchContent')
        books = db.execute("SELECT * FROM books WHERE lower({searchType}) LIKE lower('%{searchContent}%')".
                           format(searchType=searchType, searchContent=searchContent)).fetchall()

    return render_template("search.html", books=books)


@app.route('/book/<isbn>', methods=['GET', 'POST'])
def book(isbn):
    current_user = session["username"]
    if request.method == 'GET':
        b_id = db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn": isbn})
        if b_id is None:
            return "No book match"
        bookId = b_id.fetchall()

        res = requests.get("https://www.goodreads.com/book/review_counts.json",
                           params={"key": "kN50oPWehDm2yQcyaqUHg", "isbns": isbn})
        data = res.json()
        average_rating = data['books'][0]['average_rating']
        rating_count = data['books'][0]['work_ratings_count']
        return render_template("book.html", bookId=bookId, average_rating=average_rating, rating_count=rating_count)
    if request.method == 'POST':
        existing = db.execute("SELECT isbn, username FROM reviews WHERE username=:username AND isbn=:isbn",
                              {"username": current_user, "isbn": isbn}).fetchone()
        rating = request.form.get("rating")
        comment = request.form.get("comment")
        if existing is not None:
            flash('Review already submitted')
            return redirect("/book/" + isbn)
        else:
            db.execute("INSERT INTO reviews(isbn, username, ratings, comment) VALUES(:isbn, :username, :ratings, "
                       ":comment)",
                       {"isbn": isbn, "username": current_user, "ratings": rating, "comment": comment})
            db.commit()
            flash("your review is submitted")
            return redirect("/book/" + isbn)


if __name__ == '__main__':
    app.run(debug=True)
