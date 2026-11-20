"""
notification_config.py — In-Code Email (SMTP) & SMS (Twilio) Configuration.

Configured for Sugar Plant Predictive Maintenance.
"""

# ==============================================================================
# 1. EMAIL NOTIFICATIONS CONFIGURATION (SMTP - Gmail)
# ==============================================================================
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USE_TLS = True

# Primary Sender Gmail Account:
SMTP_USER = "bongiwepatriciasimelane@gmail.com"

# Google App Password (16 characters, no spaces):
SMTP_PASSWORD = "hlcuyisefwxtcbtu"

# Sender Display Header:
EMAIL_FROM = "SugarPlant Maintenance <bongiwepatriciasimelane@gmail.com>"


# ==============================================================================
# 2. SMS NOTIFICATIONS CONFIGURATION (Twilio)
# ==============================================================================
# Twilio Console: https://console.twilio.com/
TWILIO_ACCOUNT_SID = ""
TWILIO_AUTH_TOKEN = ""
TWILIO_PHONE_NUMBER = ""
