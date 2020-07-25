import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def review_table():
    db.execute(
        "CREATE TABLE Reviews (review_id SERIAL, title VARCHAR, text VARCHAR, book_id INTEGER, PRIMARY KEY(review_id), CONSTRAINT U_review UNIQUE (review_id), CONSTRAINT FK_bookID FOREIGN KEY (book_id) REFERENCES books(book_id));"
    )
    db.commit()

# review_table()

def add_user_review():
    db.execute("ALTER TABLE reviews ADD user_id INTEGER, ADD CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES Users (user_id);")
    db.commit()

# add_user_review()

def add_rating_column():
    db.execute("ALTER TABLE reviews ADD rating INTEGER NOT NULL;")
    db.commit()

# add_rating_column()

def add_review_count_score_books():
    db.execute("ALTER TABLE books ADD review_count INTEGER, ADD avg_score DECIMAL(3,2)")
    db.commit()

add_review_count_score_books()