import os

from flask import Flask, session
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import render_template, request, redirect, url_for, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import requests
import simplejson as json

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
    return redirect(url_for("home"))

@app.route("/home")
def home():
    if not session.get("logged_in"):
        return render_template("index.html")

    return render_template("dashboard.html", username=session["user"], name=session["first_name"])

@app.route("/search", methods=["POST", "GET"])
def search():
    if not session.get("logged_in"):
        # message="You are not logged in!"
        return method_not_allowed(405)

    search_info = request.form.get("search")

    #search in datasabe any record that contains the user search text
    search_results = db.execute("SELECT isbn, title, author, year FROM books WHERE isbn ILIKE '%' || :search_info || '%' OR title ILIKE '%' || :search_info || '%' OR author ILIKE '%' || :search_info || '%'", {"search_info": search_info}).fetchall()

    if not(request.method == "POST"):
        return render_template("search.html", search_results=session["search_results"], search_info=session["search_info"], username=session["user"], name=session["first_name"])

    #if there is no results
    if len(search_results) == 0:
        return render_template("dashboard.html", message="Nothing found!", username=session["user"], name=session["first_name"])


    session["search_results"] = search_results
    session["search_info"] = search_info
    
    return render_template("search.html", search_results=session["search_results"], search_info=session["search_info"], username=session["user"], name=session["first_name"])

@app.route("/books/<book_isbn>", methods=["POST", "GET"])
def books(book_isbn):
    if not session.get("logged_in"):
        message="You are not logged in!"
        return render_template("error.html", message=message)

    book_info = db.execute("SELECT book_id, isbn, title, author, year FROM books WHERE isbn = :book_isbn", {"book_isbn": book_isbn}).first()

    if book_info is None:
        return page_not_found(404)
    
    #get book grade and review numbers from goodreads API
    res_json = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key":"6Xlb1aIM9rN1KrArglfKVQ", "isbns": book_isbn}).json()    
    reviews_count_GR = res_json["books"][0]["work_reviews_count"]
    avg_rating_GR = res_json["books"][0]["average_rating"]

    user = session.get("user")

    if request.method == "POST":
        review_title = request.form.get("review_title")
        review_text = request.form.get("review_text")
        review_rating = request.form.get("review_rating")
        user_id = db.execute("SELECT user_id FROM Users WHERE username = :username", {"username": user}).first()[0]

        #check if review is empty and if the user already wrote one
        if review_rating == "":
            flash("The rating field can not be empty!", "review_form")
            return redirect(url_for('books', book_isbn=book_isbn))
        elif int(review_rating) < 1 or int(review_rating) > 5:
            flash("The rating must be between 1 and 5", "review_form")
            return redirect(url_for('books', book_isbn=book_isbn))
        elif db.execute("SELECT user_id FROM reviews WHERE user_id = :user_id AND book_id = :book_id", {"user_id": user_id, "book_id": book_info.book_id}).rowcount > 0:
            flash("You already wrote a review!", "review_form")
            return redirect(url_for('books', book_isbn=book_isbn)) 

        #insert review/rating
        db.execute("INSERT INTO reviews (rating, title, text, book_id, user_id) VALUES (:rating, :title, :text, :book_id, :user_id)", {"rating": review_rating, "title":review_title, "text": review_text, "book_id":book_info.book_id, "user_id": user_id})
        db.commit()

        count_review = db.execute("SELECT COUNT(*) FROM reviews WHERE book_id = :book_id", {"book_id": book_info.book_id}).first()[0]
        avg_score = db.execute("SELECT AVG(rating) FROM reviews WHERE book_id = :book_id", {"book_id": book_info.book_id}).first()[0]

        # update review count e avg rating in books table
        if not(review_text == ""):
            db.execute("UPDATE books SET review_count = :review_count, avg_score = :avg_score WHERE book_id = :book_id", {"review_count": count_review, "avg_score": avg_score, "book_id": book_info.book_id})
            db.commit()
        else:
            db.execute("UPDATE books SET avg_score = :avg_score WHERE book_id = :book_id", {"avg_score": avg_score, "book_id": book_info.book_id})
            db.commit()

        return redirect(url_for('books', book_isbn=book_isbn)) #PRG


    #get all reviews
    reviews = db.execute("SELECT a.*, b.username FROM reviews as a LEFT JOIN users as b ON (a.user_id=b.user_id) WHERE book_id = :book_id", {"book_id": book_info.book_id}).fetchall()

    if reviews == []:
        flash("Be the first to review this book!","none_review")
    
    return render_template("book.html", book_info=book_info, name=session["first_name"], avg_rating_GR=avg_rating_GR, reviews_count_GR=reviews_count_GR, reviews=reviews)


@app.route("/signup", methods=["POST"])
def signup():
    username = request.form.get("username")
    password = request.form.get("password")
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")

    #check if the filds are empty
    if username == "" or password == "" or first_name == "" or last_name == "":
        flash("You must fill all fields", 'signup')
        return redirect(url_for('home')) 

    #check if user already exist
    if db.execute("SELECT username FROM users WHERE username = :username", {"username": username}).rowcount >= 1:
        flash("This user already exist.", 'signup')
        return redirect(url_for('home'))
        
    #create a new user
    db.execute("INSERT INTO users (username, password, first_name, last_name) VALUES (:username, :password, :first_name, :last_name)", {"username":username, "password":generate_password_hash(password), "first_name":first_name, "last_name":last_name})
    db.commit()

    flash("Account created! Now you can login in!", "login")
    return redirect(url_for("home"))


@app.route("/login", methods=["POST", "GET"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    user = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).first()
    #check if the fields are empty
    if username == "" or password == "":
        flash("You must enter your username and password", 'login')
        return redirect(url_for('home'))
    if user is None:
        flash("Incorrect login.", "login")
        return redirect(url_for('home')) 
    elif not check_password_hash(user.password, password):
        flash("Incorrect password.", "login")
        return redirect(url_for('home')) 
    
    session['logged_in'] = True
    
    session["user"] = username
    session["first_name"] = user.first_name
    
    return render_template("dashboard.html", username=session["user"], name=session["first_name"])


@app.route("/logout")
def logout():
    session['logged_in'] = False
    session.clear()
    return home()

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message="Not found!"), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return redirect(url_for("home"))

@app.route("/api/<book_isbn>", methods=["GET"])
def api(book_isbn):
    book = db.execute("SELECT * FROM books WHERE isbn = :book_isbn", {"book_isbn":book_isbn}).fetchone()

    if book is None:
        return page_not_found(404)
    
    return jsonify (
        {
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "isbn": book_isbn,
        "review_count": book.review_count,
        "average_score": book.avg_score
        }
    )
