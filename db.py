from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Settings
from config import MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB, MYSQL_PORT

DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    # ensure a single settings row exists
    session = SessionLocal()
    s = session.query(Settings).first()
    if not s:
        s = Settings(voting_active=False, results_declared=False)
        session.add(s)
        session.commit()
    session.close()
