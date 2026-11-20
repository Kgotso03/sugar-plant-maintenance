"""
Notifications Center and Real-Time Delivery Log Explorer Routes.
Allows users and administrators to view alert deliveries, mark as read,
and dispatch test Email/SMS notifications.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import db
from models.notification import NotificationLog
from models.user import User
from services.auth_service import login_required, get_current_user
from services.notification_service import notification_service
from services.audit_service import log_action

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/notifications")
@login_required
def index():
    user = get_current_user()
    category = request.args.get("category", "")
    channel = request.args.get("channel", "")

    query = NotificationLog.query
    # Non-admins only see notifications addressed to them
    if not user.is_admin:
        query = query.filter_by(user_id=user.id)

    if category and category in NotificationLog.CATEGORIES:
        query = query.filter_by(category=category)
    if channel and channel in NotificationLog.CHANNELS:
        query = query.filter_by(channel=channel)

    notifications = query.order_by(NotificationLog.created_at.desc()).limit(150).all()
    unread_count = NotificationLog.query.filter_by(user_id=user.id, is_read=False).count()

    return render_template(
        "notifications/index.html",
        notifications=notifications,
        unread_count=unread_count,
        categories=NotificationLog.CATEGORIES,
        channels=NotificationLog.CHANNELS,
        selected_category=category,
        selected_channel=channel,
    )


@notifications_bp.route("/notifications/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_read(notif_id):
    user = get_current_user()
    notif = NotificationLog.query.get_or_404(notif_id)

    if not user.is_admin and notif.user_id != user.id:
        flash("Unauthorized to modify this notification.", "danger")
        return redirect(url_for("notifications.index"))

    notif.is_read = True
    db.session.commit()
    return redirect(url_for("notifications.index"))


@notifications_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_read():
    user = get_current_user()
    NotificationLog.query.filter_by(user_id=user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("notifications.index"))


@notifications_bp.route("/notifications/test", methods=["POST"])
@login_required
def send_test():
    """Dispatches a test notification to the current logged-in user."""
    user = get_current_user()
    title = "[TEST NOTIFICATION] SugarPlant PM Alert System"
    message = (
        f"Hello {user.full_name or user.username},\n\n"
        f"This is a test notification from the Sugar Plant Predictive Maintenance System.\n"
        f"Your notification channels are verified and operational.\n"
        f"• Email: {user.email or 'Not configured'}\n"
        f"• Phone: {user.phone_number or 'Not configured'}\n"
        f"• Timestamp: {db.func.current_timestamp()}"
    )

    logs = notification_service.dispatch_notification(user, title, message, category=NotificationLog.CATEGORY_SYSTEM)
    log_action("SEND_TEST_NOTIFICATION", "NotificationLog", None, f"Sent test alert to {user.username}")

    channels_used = [l.channel.upper() for l in logs]
    if channels_used:
        flash(f"Test notification dispatched via: {', '.join(channels_used)}. Check the log table below.", "success")
    else:
        flash("No notification channels enabled for your account. Please update your profile with email/phone.", "warning")

    return redirect(url_for("notifications.index"))


@notifications_bp.route("/api/notifications/unread-count")
@login_required
def api_unread_count():
    user = get_current_user()
    count = NotificationLog.query.filter_by(user_id=user.id, is_read=False).count()
    return jsonify({"unread_count": count})
