"""
db_config.py — Cloud Database Configuration.

Configured with your Supabase PostgreSQL cloud database.
"""

# ==============================================================================
# PERMANENT CLOUD DATABASE CONNECTION STRING (Supabase)
# ==============================================================================
# Password '@' and '%' are URL-encoded as %40 and %25 for RFC-3986 URI standard:
CLOUD_DATABASE_URI = "postgresql://postgres:Sugarplant%40%25123@db.koefkhwxtbzzyapruqgq.supabase.co:5432/postgres"
