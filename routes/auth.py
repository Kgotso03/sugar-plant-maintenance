"""
Authentication Routes: Login, Logout, Profile.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.user import User
from services.auth_service import login_user, logout_user, get_current_user, login_required
from services.audit_service import log_action

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        try:
            user = User.query.filter((User.username == username) | (User.email == username)).first()
        except Exception as e:
            flash(f"Database connection error: Unable to reach database ({e}). Please verify your database settings.", "danger")
            return render_template("auth/login.html", username=username)

        if user and user.check_password(password):
            if not user.is_active:
                flash("Your account has been deactivated. Please contact an administrator.", "danger")
                return render_template("auth/login.html", username=username)

            login_user(user)
            log_action("LOGIN", "User", user.id, f"User {user.username} logged in successfully")
            flash(f"Welcome back, {user.full_name or user.username}!", "success")

            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("dashboard.index"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    user = get_current_user()
    if user:
        log_action("LOGOUT", "User", user.id, f"User {user.username} logged out")
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile")
@login_required
def profile():
    user = get_current_user()
    return render_template("auth/profile.html", user=user)
