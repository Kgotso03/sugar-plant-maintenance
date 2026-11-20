"""Minimal smoke tests for the Flask application."""

import pytest
from app import create_app
from extensions import db
from models.user import User


@pytest.fixture
def app():
    """Create a test application using SQLite in-memory database."""
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        # Seed a demo admin user for auth tests
        admin = User(username="admin", email="admin@test.local", role=User.ROLE_ADMIN)
        admin.set_password("Admin123!")
        db.session.add(admin)
        db.session.commit()
        yield application


@pytest.fixture
def client(app):
    """Test client bound to in-memory SQLite app."""
    with app.test_client() as test_client:
        yield test_client


def test_health_endpoint(client):
    """Health endpoint must return 200 with status:ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "sugar_plant_maintenance"


def test_database_health_endpoint(client):
    """Database health endpoint must safely check DB connectivity (SQLite in test mode)."""
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_index_serves_template(client):
    """Index route requires authentication and renders dashboard with Chart.js."""
    # When unauthenticated, redirects to login
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    # When authenticated, renders dashboard with Chart.js CDN
    client.post("/login", data={"username": "admin", "password": "Admin123!"})
    res_auth = client.get("/")
    assert res_auth.status_code == 200
    assert b"chart.js" in res_auth.data.lower()


def test_static_files_served(client):
    """Static CSS and JavaScript files must be accessible."""
    css_res = client.get("/static/css/style.css")
    assert css_res.status_code == 200
    assert b"--primary" in css_res.data

    js_res = client.get("/static/js/main.js")
    assert js_res.status_code == 200
    assert b"Sugar Plant" in js_res.data
