"""
Simple Blog Website - Flask application with JSON storage.
No database; all data in posts.json.
"""
import json
import os
import secrets
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent
POSTS_FILE = APP_DIR / "posts.json"
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# Hardcoded admin (username); password is hashed
ADMIN_USERNAME = "admin"
# Default password: "admin" - change via env or regenerate hash in production
ADMIN_PASSWORD_HASH = os.environ.get(
    "ADMIN_PASSWORD_HASH",
    generate_password_hash("admin", method="scrypt"),
)

# -----------------------------------------------------------------------------
# App setup
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["JSON_AS_ASCII"] = False


def get_csrf_token():
    """Get or create CSRF token in session."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def validate_csrf():
    """Return True if request has valid CSRF token."""
    token = request.form.get("csrf_token")
    return token and secrets.compare_digest(token, get_csrf_token())


@app.context_processor
def inject_csrf():
    return {"csrf_token": get_csrf_token()}


# -----------------------------------------------------------------------------
# Data helpers
# -----------------------------------------------------------------------------
def ensure_posts_file():
    """Create posts.json with empty list if it does not exist."""
    if not POSTS_FILE.exists():
        POSTS_FILE.write_text("[]", encoding="utf-8")
    return POSTS_FILE


def load_posts():
    """Load posts from JSON file. Return empty list on missing file or invalid JSON."""
    ensure_posts_file()
    try:
        with open(POSTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_posts(posts):
    """Write posts list to JSON file."""
    ensure_posts_file()
    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)


def get_next_id(posts):
    """Return next numeric ID (max existing + 1)."""
    if not posts:
        return 1
    return max((p.get("id", 0) for p in posts), default=0) + 1


def find_post_by_id(post_id):
    """Return post dict if found, else None. post_id can be int or string (numeric)."""
    try:
        pid = int(post_id)
    except (TypeError, ValueError):
        return None
    posts = load_posts()
    for p in posts:
        if p.get("id") == pid:
            return p
    return None


def posts_sorted_latest(posts):
    """Return posts sorted by created_at descending (latest first)."""
    def key(p):
        return p.get("created_at", "") or ""
    return sorted(posts, key=key, reverse=True)


# -----------------------------------------------------------------------------
# Auth helpers
# -----------------------------------------------------------------------------
def admin_required(f):
    """Decorator: redirect to login if not authenticated as admin."""
    from functools import wraps

    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return wrapped


# -----------------------------------------------------------------------------
# Routes - Public
# -----------------------------------------------------------------------------
@app.route("/")
def home():
    posts = load_posts()
    query = (request.args.get("q") or "").strip()
    if query:
        q = query.lower()
        posts = [p for p in posts if q in (p.get("title") or "").lower()]
    posts = posts_sorted_latest(posts)
    return render_template("home.html", posts=posts, search_query=query)


@app.route("/post/<post_id>")
def view_post(post_id):
    post = find_post_by_id(post_id)
    if post is None:
        return render_template("404.html"), 404
    return render_template("post.html", post=post)


# -----------------------------------------------------------------------------
# Routes - Auth
# -----------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("admin_logged_in"):
            return redirect(url_for("admin_dashboard"))
        return render_template("login.html")

    if not validate_csrf():
        return render_template("login.html", error="Invalid request. Please try again."), 400

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    if username != ADMIN_USERNAME:
        return render_template("login.html", error="Invalid credentials"), 401

    try:
        if not check_password_hash(ADMIN_PASSWORD_HASH, password):
            return render_template("login.html", error="Invalid credentials"), 401
    except Exception:
        return render_template("login.html", error="Invalid credentials"), 401

    session["admin_logged_in"] = True
    session.permanent = True
    return redirect(url_for("admin_dashboard"))


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("home"))


# -----------------------------------------------------------------------------
# Routes - Admin (protected)
# -----------------------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    posts = posts_sorted_latest(load_posts())
    return render_template("admin.html", posts=posts)


@app.route("/create", methods=["GET", "POST"])
@admin_required
def create_post():
    if request.method == "GET":
        return render_template("create_edit.html", post=None)

    if not validate_csrf():
        return redirect(url_for("admin_dashboard"))

    title = (request.form.get("title") or "").strip()
    content = (request.form.get("content") or "").strip()

    if not title:
        return render_template("create_edit.html", post=None, error="Title is required"), 400

    posts = load_posts()
    new_id = get_next_id(posts)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_post = {
        "id": new_id,
        "title": title,
        "content": content,
        "created_at": now,
    }
    posts.append(new_post)
    save_posts(posts)
    return redirect(url_for("view_post", post_id=new_id))


@app.route("/edit/<post_id>", methods=["GET", "POST"])
@admin_required
def edit_post(post_id):
    post = find_post_by_id(post_id)
    if post is None:
        return render_template("404.html"), 404

    if request.method == "GET":
        return render_template("create_edit.html", post=post)

    if not validate_csrf():
        return redirect(url_for("admin_dashboard"))

    title = (request.form.get("title") or "").strip()
    content = (request.form.get("content") or "").strip()

    if not title:
        return (
            render_template("create_edit.html", post={**post, "title": title, "content": content}, error="Title is required"),
            400,
        )

    posts = load_posts()
    for i, p in enumerate(posts):
        if p.get("id") == post["id"]:
            posts[i] = {
                "id": post["id"],
                "title": title,
                "content": content,
                "created_at": post.get("created_at", ""),
            }
            break
    save_posts(posts)
    return redirect(url_for("view_post", post_id=post["id"]))


@app.route("/delete/<post_id>", methods=["POST"])
@admin_required
def delete_post(post_id):
    if not validate_csrf():
        return redirect(url_for("admin_dashboard"))
    post = find_post_by_id(post_id)
    if post is None:
        return render_template("404.html"), 404

    posts = load_posts()
    posts = [p for p in posts if p.get("id") != post["id"]]
    save_posts(posts)
    return redirect(url_for("admin_dashboard"))


# -----------------------------------------------------------------------------
# Error handlers
# -----------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# -----------------------------------------------------------------------------
# Run
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    ensure_posts_file()
    app.run(debug=True, host="0.0.0.0", port=5000)
