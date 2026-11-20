"""
Authentication and Role-Based Access Control (RBAC) helpers.
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify, g
from extensions import db
from models.user import User


def login_user(user: User):
    """Sets session attributes for logged-in user."""
    session.clear()
    session["user_id"] = user.id
    session["username"] = user.username
    session["role"] = user.role
    session["full_name"] = user.full_name or user.username
    session.permanent = True


def logout_user():
    """Clears current session."""
    session.clear()


def get_current_user():
    """Retrieves current user object from database or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    if not hasattr(g, "current_user") or g.current_user is None or g.current_user.id != user_id:
        g.current_user = db.session.get(User, user_id)
    return g.current_user


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_active:
            session.clear()
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized. Please log in."}), 401
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)

    return decorated_function


def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user or not user.is_active:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"error": "Unauthorized"}), 401
                flash("Please sign in to access this page.", "warning")
                return redirect(url_for("auth.login", next=request.path))

            if user.role not in allowed_roles:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"error": "Forbidden: insufficient permissions"}), 403
                flash("Access denied: You do not have permission to view or perform this action.", "danger")
                return redirect(url_for("dashboard.index"))

            return f(*args, **kwargs)

        return decorated_function

    return decorator
