
from getpass import getpass

from app import app
from models import User
from extensions import db
from werkzeug.security import generate_password_hash


with app.app_context():
    username = input("Username: ").strip()
    password = getpass("Password (minimum 12 characters): ")

    if not username:
        raise SystemExit("Username cannot be empty.")

    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters.")

    role = input("Role (admin/staff) [admin]: ").strip().lower()
    role = role or "admin"

    if role not in ("admin", "staff"):
        raise SystemExit("Role must be admin or staff.")

    if User.query.filter_by(username=username).first():
        raise SystemExit("That username already exists.")

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role=role
    )

    db.session.add(user)
    db.session.commit()

    print(f"User '{username}' created with role '{role}'.")
