import sys
import hashlib
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.dataset import Dataset
from app.services.storage_service import get_storage_service

def backfill_content_hashes(db: Session | None = None) -> int:
    """
    Backfills SHA-256 content_hash for all existing dataset rows where content_hash is NULL.
    """
    owns_session = False
    if db is None:
        db = SessionLocal()
        owns_session = True

    storage = get_storage_service()
    try:
        datasets = db.query(Dataset).filter(
            (Dataset.content_hash == None) | (Dataset.content_hash == "")
        ).all()

        print(f"Found {len(datasets)} dataset(s) needing content_hash backfill.")
        updated_count = 0

        for ds in datasets:
            try:
                file_bytes = storage.get_file_bytes(ds.file_path)
                sha256_hash = hashlib.sha256(file_bytes).hexdigest()
                ds.content_hash = sha256_hash
                updated_count += 1
                print(f"  [OK] Dataset {ds.id} (Project {ds.project_id}, v{ds.version_number}) -> {sha256_hash}")
            except Exception as e:
                print(f"  [ERROR] Failed to hash file for Dataset {ds.id} ({ds.file_path}): {e}")

        db.commit()
        print(f"Successfully backfilled content_hash for {updated_count} dataset(s).")
        return updated_count
    except Exception as e:
        db.rollback()
        print(f"Error during backfill: {e}")
        raise
    finally:
        if owns_session:
            db.close()

if __name__ == "__main__":
    backfill_content_hashes()
