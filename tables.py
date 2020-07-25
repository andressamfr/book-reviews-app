import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    db.execute("CREATE TABLE Books (book_id SERIAL PRIMARY KEY, ISBN VARCHAR NOT NULL, title VARCHAR NOT NULL, author VARCHAR NOT NULL, year INTEGER NOT NULL, CONSTRAINT U_Book UNIQUE (book_id,ISBN)); CREATE TABLE Users (user_id SERIAL PRIMARY KEY, username VARCHAR NOT NULL, password VARCHAR NOT NULL,first_name VARCHAR NOT NULL, last_name VARCHAR NOT NULL, CONSTRAINT U_User UNIQUE (user_id,username));")
    db.commit()

if __name__ == "__main__":
    main()