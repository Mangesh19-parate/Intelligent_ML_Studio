"""
Standalone script to seed demonstration accounts for local development.
Usage:
    python backend/scripts/seed_demo.py
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.core.config import settings
from app.core.seeder import seed_rbac_data, seed_demo_accounts

def main():
    if settings.ENV.lower() == "production":
        print("ERROR: Cannot seed demo accounts in production environment!", file=sys.stderr)
        sys.exit(1)
        
    db = SessionLocal()
    try:
        print("Ensuring RBAC roles and permissions exist...")
        seed_rbac_data(db)
        print("Seeding demo accounts (trainer@demo.com and approver@demo.com)...")
        seed_demo_accounts(db)
        print("Successfully seeded demo accounts!")
    finally:
        db.close()

if __name__ == "__main__":
    main()
