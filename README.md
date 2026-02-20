# Simple Blog

A lightweight blog web application built with **Flask**. No database — all posts are stored in a JSON file.

## Features

- **Public:** View posts, search by title
- **Admin:** Login to create, edit, and delete posts
- Session-based authentication with hashed passwords
- Bootstrap UI, custom 404, CSRF protection

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the app

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

### 3. Admin login

- **Username:** `admin`
- **Password:** `admin`

Change the password in production (see below).

## Project Structure

```
blog/
├── app.py              # Flask app and routes
├── posts.json          # Blog data (created if missing)
├── requirements.txt
├── templates/          # Jinja2 templates
└── static/
    ├── css/style.css
    └── images/
```

## Production / Deploy

1. **Set environment variables:**
   - `SECRET_KEY` — random secret for session signing
   - `ADMIN_PASSWORD_HASH` — set via Python:
     ```python
     from werkzeug.security import generate_password_hash
     print(generate_password_hash("your-secure-password", method="scrypt"))
     ```

2. **Run with a WSGI server** (e.g. Gunicorn):

   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

## Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Home — list posts, search |
| GET | `/post/<id>` | View single post |
| GET/POST | `/login` | Admin login |
| GET | `/logout` | Logout |
| GET | `/admin` | Admin dashboard (protected) |
| GET/POST | `/create` | Create post (protected) |
| GET/POST | `/edit/<id>` | Edit post (protected) |
| POST | `/delete/<id>` | Delete post (protected) |

## Tech Stack

- **Backend:** Python, Flask
- **Storage:** JSON file (`posts.json`)
- **Templates:** Jinja2
- **Auth:** Flask session, Werkzeug password hashing
- **Frontend:** HTML, Bootstrap 5, CSS
