"""
db_config.py — Cloud Database Configuration.

Vercel is serverless, so SQLite in /tmp/ gets wiped whenever the server sleeps.
To keep your data permanently, paste a free cloud PostgreSQL or MySQL connection string below.
"""

# ==============================================================================
# PERMANENT CLOUD DATABASE CONNECTION STRING
# ==============================================================================
# Examples:
#   Neon (recommended, 100% free):
#   CLOUD_DATABASE_URI = "postgresql://neondb_owner:npg_xxxx@ep-cool-pond-xxxx.us-east-2.aws.neon.tech/neondb?sslmode=require"
#
#   Supabase (free PostgreSQL):
#   CLOUD_DATABASE_URI = "postgresql://postgres:YourPassword@db.xxxx.supabase.co:5432/postgres"
# ==============================================================================

CLOUD_DATABASE_URI = ""
