import sys

packages = [
    ("Flask", "flask"),
    ("Flask-SQLAlchemy", "flask_sqlalchemy"),
    ("Flask-Migrate", "flask_migrate"),
    ("Flask-WTF", "flask_wtf"),
    ("Flask-Login", "flask_login"),
    ("python-dotenv", "dotenv"),
    ("PyMySQL", "pymysql"),
    ("pandas", "pandas"),
    ("NumPy", "numpy"),
    ("scikit-learn", "sklearn"),
    ("joblib", "joblib"),
    ("matplotlib", "matplotlib"),
    ("pytest", "pytest"),
    ("pytest-flask", "pytest_flask"),
    ("email-validator", "email_validator"),
]

results = []
all_ok = True
for name, mod_name in packages:
    try:
        mod = __import__(mod_name)
        ver = getattr(mod, "__version__", "installed")
        results.append((name, "OK", ver))
    except Exception as e:
        all_ok = False
        results.append((name, "FAILED", str(e)))

print("=== PACKAGE VERIFICATION RESULTS ===")
for name, status, ver in results:
    print(f"[{status}] {name:<18} : {ver}")

if not all_ok:
    sys.exit(1)
print("\nAll required packages are functional!")

