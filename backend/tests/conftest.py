import sys
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.core.seeder import seed_rbac_data
from app.core.config import settings
from app.services.storage_service import LocalStorageService, get_storage_service
from app.models.user import User
from app.models.role import Role
from app.main import app

# Use in-memory SQLite database with StaticPool for test isolation
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_storage(tmp_path_factory):
    tmp_storage = tmp_path_factory.mktemp("storage")
    settings.STORAGE_LOCAL_DIR = str(tmp_storage)

@pytest.fixture(scope="function")
def db_session(tmp_path):
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_rbac_data(db)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def create_test_user(db_session):
    def _create(email: str, role_name: str = "ML_ENGINEER", full_name: str = "Test User"):
        role = db_session.query(Role).filter(Role.role_name == role_name).first()
        user = User(
            id=uuid.uuid4(),
            full_name=full_name,
            email=email,
            password_hash=get_password_hash("password123"),
            role_id=role.id,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    return _create
