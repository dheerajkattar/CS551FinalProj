import os
import uuid
import logging
import time
from functools import wraps
from datetime import datetime, timedelta, timezone

from flask import Flask, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# -------------------------
# LOGGING
# -------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# -------------------------
# DATABASE
# -------------------------
db_url = os.getenv("DATABASE_URL", "sqlite:///notes.db")

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

if db_url.startswith("sqlite"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
else:
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": int(os.getenv("DB_POOL_SIZE", 10)),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", 0)),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", 3600)),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", 30)),
        "pool_pre_ping": True,
    }

db = SQLAlchemy(app)
SESSION_HOURS = int(os.getenv("SESSION_HOURS", 24))


# -------------------------
# MODELS
# -------------------------
class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    notes = db.relationship("Note", backref="owner", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {"id": self.id, "username": self.username, "email": self.email}


class UserSession(db.Model):
    __tablename__ = "user_session"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    user = db.relationship("User")

    def is_valid(self):
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return self.is_active and expires > now


class Note(db.Model):
    __tablename__ = "note"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.String(1000))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "body": self.body,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# -------------------------
# HELPERS
# -------------------------
def initialize_database():
    with app.app_context():
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db.create_all()
        logger.info("Database initialized")


def get_token():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "").strip()
    return request.headers.get("X-Session-Token")


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = get_token()

        if not token:
            return jsonify({"error": "Missing session token"}), 401

        user_session = UserSession.query.filter_by(token=token, is_active=True).first()

        if not user_session or not user_session.is_valid():
            return jsonify({"error": "Invalid or expired session"}), 401

        g.current_user = user_session.user
        g.current_session = user_session
        return f(*args, **kwargs)

    return wrapper


@app.before_request
def log_request():
    request.start_time = time.time()
    logger.info("%s %s", request.method, request.path)


@app.after_request
def log_response(response):
    duration = time.time() - getattr(request, "start_time", time.time())
    logger.info("%s %s -> %s %.4fs", request.method, request.path, response.status_code, duration)
    return response


@app.errorhandler(Exception)
def handle_error(e):
    logger.exception("Unhandled exception")
    return jsonify({"error": "Internal server error"}), 500


# -------------------------
# AUTH ROUTES
# -------------------------
@app.route("/auth/register", methods=["POST"])
def register():
    data = request.json or {}

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "Missing username, email, or password"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 409

    user = User(username=username, email=email)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User registered", "user": user.to_dict()}), 201


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.json or {}

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

    token = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)

    user_session = UserSession(
        token=token,
        user_id=user.id,
        expires_at=expires_at,
    )

    db.session.add(user_session)
    db.session.commit()

    return jsonify({
        "message": "Login successful",
        "user": user.to_dict(),
        "session_token": token,
        "expires_at": expires_at.isoformat(),
    }), 200


@app.route("/auth/logout", methods=["POST"])
@login_required
def logout():
    g.current_session.is_active = False
    db.session.commit()
    return jsonify({"message": "Logout successful"}), 200


# -------------------------
# NOTE ROUTES
# -------------------------
@app.route("/notes", methods=["POST"])
@login_required
def create_note():
    data = request.json or {}

    title = data.get("title")
    body = data.get("body")

    if not title:
        return jsonify({"error": "Missing note title"}), 400

    note = Note(
        user_id=g.current_user.id,
        title=title,
        body=body,
    )

    db.session.add(note)
    db.session.commit()

    return jsonify(note.to_dict()), 201


@app.route("/notes", methods=["GET"])
@login_required
def get_notes():
    notes = Note.query.filter_by(user_id=g.current_user.id).all()
    return jsonify([note.to_dict() for note in notes]), 200


@app.route("/notes/<int:note_id>", methods=["GET"])
@login_required
def get_note(note_id):
    note = Note.query.filter_by(id=note_id, user_id=g.current_user.id).first()

    if not note:
        return jsonify({"error": "Note not found"}), 404

    return jsonify(note.to_dict()), 200


@app.route("/notes/<int:note_id>", methods=["DELETE"])
@login_required
def delete_note(note_id):
    note = Note.query.filter_by(id=note_id, user_id=g.current_user.id).first()

    if not note:
        return jsonify({"error": "Note not found"}), 404

    db.session.delete(note)
    db.session.commit()

    return jsonify({"message": "Note deleted", "note": note.to_dict()}), 200


# -------------------------
# HEALTH
# -------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


# -------------------------
# ENTRYPOINT
# -------------------------
if os.getenv("SKIP_DB_INIT") != "1":
    initialize_database()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=os.getenv("FLASK_DEBUG") == "1",
    )