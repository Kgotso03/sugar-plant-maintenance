import os
import sys

# Ensure parent directory is in Python path for Vercel serverless environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

