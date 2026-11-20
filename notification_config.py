"""
notification_config.py — In-Code Email (SMTP) & SMS (Twilio) Configuration.

You can configure your real email and SMS credentials directly in this file.
Once saved, notifications will immediately dispatch via these accounts.
"""

# ==============================================================================
# 1. EMAIL NOTIFICATIONS CONFIGURATION (SMTP)
# ==============================================================================
# For Gmail:
#   1. Go to https://myaccount.google.com/apppasswords
#   2. Create an App password named "SugarPlant"
#   3. Paste the 16-character code below into SMTP_PASSWORD.
# ==============================================================================

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USE_TLS = True

# Put your Gmail/Work email address here:
SMTP_USER = ""

# Put your 16-character App Password here:
SMTP_PASSWORD = ""

# The name and email address recipients see as the sender:
EMAIL_FROM = "SugarPlant Maintenance <notifications@sugarplant.local>"


# ==============================================================================
# 2. SMS NOTIFICATIONS CONFIGURATION (Twilio)
# ==============================================================================
# Get these from your Twilio Console (https://console.twilio.com/):
# ==============================================================================

# Put your Twilio Account SID here (starts with AC...):
TWILIO_ACCOUNT_SID = ""

# Put your Twilio Auth Token here:
TWILIO_AUTH_TOKEN = ""

# Put your Twilio Phone Number here (e.g. "+12345678901"):
TWILIO_PHONE_NUMBER = ""
