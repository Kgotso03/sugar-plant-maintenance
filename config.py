"""
config.py — Configuration classes for the Sugar Plant Maintenance application.
Select a configuration by setting FLASK_ENV in .env.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "SQLALCHEMY_DATABASE_URI",
        "mysql+pymysql://root:@127.0.0.1:3306/sugar_plant_maintenance",
    )

    # In-code Notification Settings (see notification_config.py)
    try:
        import notification_config
        SMTP_HOST = notification_config.SMTP_HOST
        SMTP_PORT = notification_config.SMTP_PORT
        SMTP_USER = notification_config.SMTP_USER
        SMTP_PASSWORD = notification_config.SMTP_PASSWORD
        SMTP_USE_TLS = notification_config.SMTP_USE_TLS
        EMAIL_FROM = notification_config.EMAIL_FROM
        TWILIO_ACCOUNT_SID = notification_config.TWILIO_ACCOUNT_SID
        TWILIO_AUTH_TOKEN = notification_config.TWILIO_AUTH_TOKEN
        TWILIO_PHONE_NUMBER = notification_config.TWILIO_PHONE_NUMBER
    except Exception:
        pass


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = False


class TestingConfig(BaseConfig):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False


config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}

