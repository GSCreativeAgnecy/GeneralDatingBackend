import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def sample_user():
    return {
        "id": 1,
        "phone_number": "9990000000",
        "phone_verified": True,
        "email": None,
        "password_hash": "hashed_password",
        "name": "Test User",
        "date_of_birth": "1995-06-15",
        "gender": "male",
        "bio": "Test bio",
        "intent": "lets_see",
        "city": "Mumbai",
        "college": None,
        "workplace": None,
        "height_cm": 175,
        "religion": None,
        "education": None,
        "occupation": None,
        "photo_verified": True,
        "profile_complete": True,
        "is_premium": False,
        "is_active": True,
        "last_active": None,
        "location_lat": 19.0760,
        "location_lng": 72.8777,
        "preferred_language": "en",
        "show_online_status": True,
        "show_distance": True,
        "created_at": None,
        "updated_at": None,
    }
