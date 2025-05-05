
"""SQLite DB ORM interface for Fetch Bites Agent

Dependencies:
- SQLAlchemy

Install via:
pip install sqlalchemy
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError

Base = declarative_base()
DB_PATH = "sqlite:///fetch_bites.db"
engine = create_engine(DB_PATH)
Session = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    ig_handle = Column(String, unique=True)
    email = Column(String)
    onboarded = Column(Boolean, default=False)
    last_processed_message_id = Column(String)

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    ig_handle = Column(String)
    message_id = Column(String)
    timestamp = Column(String)
    message_type = Column(String)  # 'text', 'post', 'link'
    content = Column(Text)
    processed = Column(Boolean, default=False)

class Recipe(Base):
    __tablename__ = 'recipes'
    id = Column(Integer, primary_key=True)
    message_id = Column(String)
    ig_handle = Column(String)
    recipe_title = Column(String)
    pdf_path = Column(String)
    success = Column(Boolean, default=True)

def init_db():
    Base.metadata.create_all(engine)

def get_or_create_user(session, ig_handle):
    user = session.query(User).filter_by(ig_handle=ig_handle).first()
    if not user:
        user = User(ig_handle=ig_handle)
        session.add(user)
        session.commit()
    return user

def log_message(session, ig_handle, message_id, msg_type, content, timestamp):
    msg = Message(ig_handle=ig_handle, message_id=message_id, message_type=msg_type,
                  content=content, timestamp=timestamp)
    session.add(msg)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()

def get_unprocessed_messages(session, ig_handle):
    return session.query(Message).filter_by(ig_handle=ig_handle, processed=False).all()

def mark_message_processed(session, message_id):
    msg = session.query(Message).filter_by(message_id=message_id).first()
    if msg:
        msg.processed = True
        session.commit()

def record_recipe(session, message_id, ig_handle, title, pdf_path):
    recipe = Recipe(message_id=message_id, ig_handle=ig_handle,
                    recipe_title=title, pdf_path=pdf_path)
    session.add(recipe)
    session.commit()
