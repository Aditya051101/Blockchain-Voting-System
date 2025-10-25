# create_admin.py
from db import init_db, SessionLocal
from models import User, RoleEnum
from werkzeug.security import generate_password_hash
import getpass

def main():
    init_db()
    username = input("Admin username: ").strip()
    pwd = getpass.getpass("Admin password: ")
    session = SessionLocal()
    hashed = generate_password_hash(pwd)
    u = User(username=username, password=hashed, role=RoleEnum.admin)
    session.add(u)
    session.commit()
    print("Admin created.")
    session.close()

if __name__ == "__main__":
    main()
