"""
Notification Service for Sugar Plant Predictive Maintenance System.
Dispatches critical operational alerts, work order assignments, PM schedule reminders,
and login credential notifications via Email (SMTP) and SMS (Twilio/Gateway).
Includes simulation fallback logger for local development and offline environments.
"""
import os
import sys
import smtplib
import urllib.request
import urllib.parse
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from flask import current_app, has_app_context
from extensions import db
from models.notification import NotificationLog
from models.user import User

try:
    import notification_config
except ImportError:
    notification_config = None


class NotificationService:
    @staticmethod
    def send_email(to_email: str, subject: str, text_body: str, html_body: str = None) -> tuple[bool, str]:
        """
        Sends an email using standard SMTP.
        Falls back to console logger if SMTP is not configured or offline.
        """
        if not to_email:
            return False, "Recipient email is empty"

        smtp_host = (
            getattr(notification_config, "SMTP_HOST", "")
            or os.environ.get("SMTP_HOST", "")
            or "smtp.gmail.com"
        ).strip()

        smtp_user = (
            getattr(notification_config, "SMTP_USER", "")
            or os.environ.get("SMTP_USER", "")
            or "bongiwepatriciasimelane@gmail.com"
        ).strip()

        smtp_password = (
            getattr(notification_config, "SMTP_PASSWORD", "")
            or os.environ.get("SMTP_PASSWORD", "")
            or "hlcuyisefwxtcbtu"
        ).strip()

        try:
            smtp_port = int(getattr(notification_config, "SMTP_PORT", None) or os.environ.get("SMTP_PORT", 587))
        except (ValueError, TypeError):
            smtp_port = 587

        raw_tls = getattr(notification_config, "SMTP_USE_TLS", None)
        if raw_tls is None:
            smtp_use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
        else:
            smtp_use_tls = bool(raw_tls)

        raw_from = (
            getattr(notification_config, "EMAIL_FROM", "")
            or os.environ.get("EMAIL_FROM", "")
            or "SugarPlant Maintenance"
        ).strip()

        # Build RFC-compliant From header and SMTP envelope sender
        if "@" in raw_from:
            display_from = raw_from
            sender_addr = smtp_user or raw_from
        else:
            display_from = f"{raw_from} <{smtp_user}>" if smtp_user else raw_from
            sender_addr = smtp_user

        # Live SMTP dispatch
        is_testing = has_app_context() and current_app.config.get("TESTING", False)
        if smtp_host and smtp_user and smtp_password and not is_testing:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = display_from
                msg["To"] = to_email

                part1 = MIMEText(text_body, "plain", "utf-8")
                msg.attach(part1)

                if html_body:
                    part2 = MIMEText(html_body, "html", "utf-8")
                    msg.attach(part2)

                server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                if smtp_use_tls:
                    server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(sender_addr, [to_email], msg.as_string())
                server.quit()
                return True, "Email sent successfully via SMTP"
            except Exception as e:
                err = f"SMTP error: {e}"
                print(f"[NOTIFICATION ERROR] {err}", file=sys.stderr)
                return False, err
        else:
            # Simulated local log
            print(f"\n[EMAIL SIMULATION] ===============================")
            print(f"To:      {to_email}")
            print(f"Subject: {subject}")
            print(f"Body:\n{text_body}")
            print(f"=================================================\n")
            return True, "Simulated: Logged locally (SMTP not configured in environment)"

    @staticmethod
    def send_sms(to_phone: str, message: str) -> tuple[bool, str]:
        """
        Sends an SMS message using Twilio or generic SMS gateway.
        Falls back to console logger if SMS credentials are not configured.
        """
        if not to_phone:
            return False, "Recipient phone number is empty"

        twilio_sid = (getattr(notification_config, "TWILIO_ACCOUNT_SID", "") or os.environ.get("TWILIO_ACCOUNT_SID", "")).strip()
        twilio_token = (getattr(notification_config, "TWILIO_AUTH_TOKEN", "") or os.environ.get("TWILIO_AUTH_TOKEN", "")).strip()
        twilio_from = (getattr(notification_config, "TWILIO_PHONE_NUMBER", "") or os.environ.get("TWILIO_PHONE_NUMBER", "")).strip()

        is_testing = has_app_context() and current_app.config.get("TESTING", False)
        if twilio_sid and twilio_token and twilio_from and not is_testing:
            try:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
                data = urllib.parse.urlencode({
                    "From": twilio_from,
                    "To": to_phone,
                    "Body": message,
                }).encode("utf-8")

                req = urllib.request.Request(url, data=data, method="POST")
                auth = base64.b64encode(f"{twilio_sid}:{twilio_token}".encode("ascii")).decode("ascii")
                req.add_header("Authorization", f"Basic {auth}")
                req.add_header("Content-Type", "application/x-www-form-urlencoded")

                with urllib.request.urlopen(req, timeout=6) as response:
                    if response.status in (200, 201):
                        return True, "SMS sent successfully via Twilio"
                    return False, f"Twilio HTTP {response.status}"
            except Exception as e:
                err = f"SMS gateway error: {e}"
                print(f"[NOTIFICATION ERROR] {err}", file=sys.stderr)
                return False, err
        else:
            # Simulated local log
            print(f"\n[SMS SIMULATION] =================================")
            print(f"To:      {to_phone}")
            print(f"Message: {message}")
            print(f"=================================================\n")
            return True, "Simulated: Logged locally (Twilio/SMS not configured in environment)"

    @classmethod
    def dispatch_notification(
        cls,
        user: User,
        title: str,
        message: str,
        category: str = NotificationLog.CATEGORY_SYSTEM,
        force_channels: list = None,
    ) -> list[NotificationLog]:
        """
        Dispatches notification across user's active channels (Email, SMS)
        and persists delivery records to the NotificationLog database.
        """
        logs = []
        if not user:
            return logs

        # 1. Email Channel
        send_email = user.email_notifications if force_channels is None else (NotificationLog.CHANNEL_EMAIL in force_channels)
        if send_email and user.email:
            ok, status_msg = cls.send_email(user.email, title, message)
            log_status = NotificationLog.STATUS_SENT if ok else NotificationLog.STATUS_FAILED
            err = status_msg if not ok else None
            log = NotificationLog(
                user_id=user.id,
                recipient_email=user.email,
                recipient_phone=None,
                channel=NotificationLog.CHANNEL_EMAIL,
                category=category,
                title=title,
                message=message,
                status=log_status,
                error_message=err,
                is_read=False,
            )
            db.session.add(log)
            logs.append(log)

        # 2. SMS Channel
        send_sms = user.sms_notifications if force_channels is None else (NotificationLog.CHANNEL_SMS in force_channels)
        if send_sms and user.phone_number:
            sms_text = f"SugarPlant PM: {title}\n{message}"
            if len(sms_text) > 160:
                sms_text = sms_text[:157] + "..."
            ok, status_msg = cls.send_sms(user.phone_number, sms_text)
            log_status = NotificationLog.STATUS_SENT if ok else NotificationLog.STATUS_FAILED
            err = status_msg if not ok else None
            log = NotificationLog(
                user_id=user.id,
                recipient_email=None,
                recipient_phone=user.phone_number,
                channel=NotificationLog.CHANNEL_SMS,
                category=category,
                title=title,
                message=sms_text,
                status=log_status,
                error_message=err,
                is_read=False,
            )
            db.session.add(log)
            logs.append(log)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[NOTIFICATION DB ERROR] {e}", file=sys.stderr)

        return logs

    # ── High-Level Event Handlers ─────────────────────────────────────────────

    @classmethod
    def notify_user_account_created(cls, user: User, plain_password: str, login_url: str = None):
        """Notifies newly registered user with their username, password, and login URL."""
        login_link = login_url or "https://your-sugarplant-app.vercel.app/login"
        title = "Your SugarPlant PM Access Credentials"
        message = (
            f"Hello {user.full_name or user.username},\n\n"
            f"Your system account has been initialized on the Sugar Plant Predictive Maintenance System.\n\n"
            f"Account Details:\n"
            f"• Username: {user.username}\n"
            f"• Temporary Password: {plain_password}\n"
            f"• System Role: {user.role.replace('_', ' ').title()}\n"
            f"• Login Portal: {login_link}\n\n"
            f"Please sign in and change your password immediately."
        )
        return cls.dispatch_notification(user, title, message, category=NotificationLog.CATEGORY_ACCOUNT)

    @classmethod
    def notify_user_password_changed(cls, user: User, new_password: str, login_url: str = None):
        """Notifies user when their account password has been reset."""
        login_link = login_url or "https://your-sugarplant-app.vercel.app/login"
        title = "Your SugarPlant PM Password Was Updated"
        message = (
            f"Hello {user.full_name or user.username},\n\n"
            f"Your account password for SugarPlant PM was successfully updated by an administrator.\n\n"
            f"New Credentials:\n"
            f"• Username: {user.username}\n"
            f"• Password: {new_password}\n"
            f"• Login Portal: {login_link}\n\n"
            f"If you did not request this change, please alert plant IT immediately."
        )
        return cls.dispatch_notification(user, title, message, category=NotificationLog.CATEGORY_ACCOUNT)

    @classmethod
    def notify_work_order_assigned(cls, work_order, base_url: str = None):
        """Notifies assigned technician when a work order is dispatched."""
        if not work_order.assigned_to:
            return []

        tech = work_order.assigned_to
        equip_name = work_order.equipment.name if work_order.equipment else f"Asset #{work_order.equipment_id}"
        equip_tag = work_order.equipment.equipment_tag if work_order.equipment else ""
        due_str = work_order.due_date.strftime("%Y-%m-%d") if work_order.due_date else "Immediate"

        title = f"[Work Order] {work_order.work_order_number} Assigned ({work_order.priority.upper()})"
        message = (
            f"Hello {tech.full_name or tech.username},\n\n"
            f"A maintenance work order has been assigned to you:\n\n"
            f"• Work Order: {work_order.work_order_number}\n"
            f"• Equipment: {equip_name} ({equip_tag})\n"
            f"• Task Title: {work_order.title}\n"
            f"• Priority: {work_order.priority.upper()}\n"
            f"• Due Date: {due_str}\n"
            f"• Description: {work_order.problem_description or 'No details provided'}\n\n"
            f"Please review and update the work order status once inspection begins."
        )
        return cls.dispatch_notification(tech, title, message, category=NotificationLog.CATEGORY_WORK_ORDER)

    @classmethod
    def notify_work_order_status(cls, work_order, old_status: str, new_status: str, base_url: str = None):
        """Notifies assigned technician and creator when work order status changes."""
        targets = set()
        if work_order.assigned_to:
            targets.add(work_order.assigned_to)
        if work_order.created_by:
            targets.add(work_order.created_by)

        title = f"[Work Order] {work_order.work_order_number} Status: {new_status.replace('_', ' ').title()}"
        message = (
            f"Work Order {work_order.work_order_number} ({work_order.title}) "
            f"status changed from '{old_status.upper()}' to '{new_status.upper()}'.\n"
            f"Equipment: {work_order.equipment.name if work_order.equipment else 'N/A'}\n"
            f"Completion reason / notes: {work_order.completion_reason or work_order.repair_actions or '-'}"
        )

        all_logs = []
        for u in targets:
            logs = cls.dispatch_notification(u, title, message, category=NotificationLog.CATEGORY_WORK_ORDER)
            all_logs.extend(logs)
        return all_logs

    @classmethod
    def notify_fault_alert(cls, alert, escalated: bool = False, base_url: str = None):
        """
        Notifies technicians and maintenance engineers when a WARNING or CRITICAL
        fault alert is detected or escalated.
        """
        severity_label = alert.severity.upper()
        prefix = "CRITICAL ALARM" if alert.severity == "critical" else "WARNING ALERT"
        if escalated:
            prefix = "ESCALATED TO CRITICAL"

        equip_tag = alert.equipment.equipment_tag if alert.equipment else f"Asset #{alert.equipment_id}"
        equip_name = alert.equipment.name if alert.equipment else "Unknown Equipment"

        title = f"[{prefix}] {equip_tag}: {alert.sensor_type.replace('_', ' ').title()}"
        message = (
            f"ATTENTION MAINTENANCE TEAM:\n\n"
            f"Fault Alert Breached on {equip_name} ({equip_tag})\n"
            f"• Severity: {severity_label}\n"
            f"• Sensor Type: {alert.sensor_type.replace('_', ' ').title()}\n"
            f"• Reading: {alert.observed_value} (Safety Limit: {alert.configured_limit})\n"
            f"• Incident Detail: {alert.description}\n"
            f"• Timestamp: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S') if alert.created_at else 'Just now'}\n\n"
            f"Please dispatch an on-shift technician to inspect the machinery."
        )

        # Broadcast to all active technicians and engineers
        on_duty_users = User.query.filter(
            User.is_active == True,
            User.role.in_([User.ROLE_ENGINEER, User.ROLE_TECHNICIAN, User.ROLE_ADMIN])
        ).all()

        all_logs = []
        for u in on_duty_users:
            logs = cls.dispatch_notification(u, title, message, category=NotificationLog.CATEGORY_FAULT_ALERT)
            all_logs.extend(logs)
        return all_logs

    @classmethod
    def notify_pm_schedule_due(cls, schedule, base_url: str = None):
        """Notifies assigned personnel when a preventive maintenance routine is due."""
        if not schedule.assigned_to:
            return []

        user = schedule.assigned_to
        equip_tag = schedule.equipment.equipment_tag if schedule.equipment else f"Asset #{schedule.equipment_id}"
        equip_name = schedule.equipment.name if schedule.equipment else ""
        task_name = getattr(schedule, "title", None) or getattr(schedule, "task_name", "Preventive Maintenance Task")

        title = f"[PM Reminder] {equip_tag}: {task_name} Due"
        message = (
            f"Hello {user.full_name or user.username},\n\n"
            f"Preventive Maintenance Schedule Reminder:\n\n"
            f"• Asset: {equip_name} ({equip_tag})\n"
            f"• Task: {task_name}\n"
            f"• Due Date: {schedule.next_due_date.strftime('%Y-%m-%d') if schedule.next_due_date else 'Today'}\n"
            f"• Recurrence: Every {schedule.interval_days} days\n"
            f"• Standard Instructions: {schedule.description or 'Refer to plant manual'}\n\n"
            f"Please complete and log the routine in SugarPlant PM."
        )
        return cls.dispatch_notification(user, title, message, category=NotificationLog.CATEGORY_PM_SCHEDULE)


# Singleton alias
notification_service = NotificationService()
