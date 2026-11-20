"""
User Management and Role-Based Access Control Routes (Admin only).
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db
from models.user import User
from services.auth_service import login_required, roles_required, get_current_user
from services.audit_service import log_action
from services.notification_service import notification_service

users_bp = Blueprint("users", __name__)


@users_bp.route("/users")
@login_required
@roles_required(User.ROLE_ADMIN)
def index():
    users = User.query.order_by(User.id.asc()).all()
    return render_template("users/index.html", users=users)


@users_bp.route("/users/new", methods=["GET", "POST"])
@login_required
@roles_required(User.ROLE_ADMIN)
def create():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        phone_number = request.form.get("phone_number", "").strip() or None
        email_notif = request.form.get("email_notifications") == "on"
        sms_notif = request.form.get("sms_notifications") == "on"
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", User.ROLE_TECHNICIAN)
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("Username, Email, and Password are required.", "danger")
            return render_template("users/form.html", user=None, roles=User.ALL_ROLES)

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or Email is already registered.", "danger")
            return render_template("users/form.html", user=None, roles=User.ALL_ROLES)

        user = User(
            username=username,
            email=email,
            phone_number=phone_number,
            email_notifications=email_notif,
            sms_notifications=sms_notif,
            full_name=full_name,
            role=role,
            is_active=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Dispatch login credentials via enabled notification channels
        try:
            notification_service.notify_user_account_created(
                user, password, url_for("auth.login", _external=True)
            )
        except Exception as e:
            print(f"[NOTIFICATION ERROR] {e}")

        log_action("CREATE_USER", "User", user.id, f"Created user {user.username} with role {user.role}")
        flash(f"User '{user.username}' created successfully and access credentials dispatched.", "success")
        return redirect(url_for("users.index"))

    return render_template("users/form.html", user=None, roles=User.ALL_ROLES)


@users_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required(User.ROLE_ADMIN)
def edit(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        phone_number = request.form.get("phone_number", "").strip() or None
        email_notif = request.form.get("email_notifications") == "on"
        sms_notif = request.form.get("sms_notifications") == "on"
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", user.role)
        new_password = request.form.get("password", "").strip()
        is_active_val = request.form.get("is_active", "1")

        if not email:
            flash("Email cannot be empty.", "danger")
            return render_template("users/form.html", user=user, roles=User.ALL_ROLES)

        duplicate = User.query.filter(User.email == email, User.id != user.id).first()
        if duplicate:
            flash("Another user is already using this email address.", "danger")
            return render_template("users/form.html", user=user, roles=User.ALL_ROLES)

        # Prevent locking out the last active admin
        if user.role == User.ROLE_ADMIN and is_active_val == "0":
            admin_count = User.query.filter_by(role=User.ROLE_ADMIN, is_active=True).count()
            if admin_count <= 1:
                flash("Cannot deactivate the last active administrator account.", "danger")
                return render_template("users/form.html", user=user, roles=User.ALL_ROLES)

        user.email = email
        user.phone_number = phone_number
        user.email_notifications = email_notif
        user.sms_notifications = sms_notif
        user.full_name = full_name
        user.role = role
        user.is_active = (is_active_val == "1")

        if new_password:
            user.set_password(new_password)
            try:
                notification_service.notify_user_password_changed(
                    user, new_password, url_for("auth.login", _external=True)
                )
            except Exception as e:
                print(f"[NOTIFICATION ERROR] {e}")
            flash("Password updated successfully and notification dispatched.", "info")

        db.session.commit()
        log_action("EDIT_USER", "User", user.id, f"Updated user {user.username}")
        flash(f"User '{user.username}' updated successfully.", "success")
        return redirect(url_for("users.index"))

    return render_template("users/form.html", user=user, roles=User.ALL_ROLES)


@users_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@roles_required(User.ROLE_ADMIN)
def toggle(user_id):
    current = get_current_user()
    if current.id == user_id:
        flash("You cannot deactivate your own account.", "danger")
        return redirect(url_for("users.index"))

    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()

    log_action("TOGGLE_USER_STATUS", "User", user.id, f"User {user.username} active set to {user.is_active}")
    flash(f"User '{user.username}' is now {'Active' if user.is_active else 'Deactivated'}.", "info")
    return redirect(url_for("users.index"))


@users_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@roles_required(User.ROLE_ADMIN)
def delete(user_id):
    current = get_current_user()

    if current.id == user_id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("users.index"))

    user = db.session.get(User, user_id)
    if user is None:
        flash("User not found.", "danger")
        return redirect(url_for("users.index"))

    # Prevent deleting the last administrator
    if user.role == User.ROLE_ADMIN:
        admin_count = User.query.filter_by(role=User.ROLE_ADMIN, is_active=True).count()
        if admin_count <= 1:
            flash("Cannot delete the last active administrator account.", "danger")
            return redirect(url_for("users.index"))

    username = user.username
    log_action("DELETE_USER", "User", user.id, f"Deleted user {username} (role: {user.role})")
    db.session.delete(user)
    db.session.commit()

    flash(f"User '{username}' has been permanently deleted.", "success")
    return redirect(url_for("users.index"))
