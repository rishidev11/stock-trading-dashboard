# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.backend.database import Base, get_db
from src.backend.main import app

# Import all your models so they're registered with Base
from src.backend.models import User, Transaction, Holding  # Import your actual model classes

# Use in-memory SQLite with a shared connection
SQLALCHEMY_TEST_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,  # This ensures the same connection is reused
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Create all tables at the start of the test session."""
    print(f"Creating tables: {Base.metadata.tables.keys()}")
    Base.metadata.create_all(bind=engine)

    # Debug: Check if tables were actually created
    from sqlalchemy import inspect
    inspector = inspect(engine)
    print(f"Tables in DB: {inspector.get_table_names()}")

    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Provide a fresh database session for each test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# Override get_db in FastAPI - SIMPLIFIED VERSION
def override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    """Test client for calling FastAPI endpoints."""
    # Clear any existing data before each test
    with engine.connect() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
        connection.commit()

    return TestClient(app)