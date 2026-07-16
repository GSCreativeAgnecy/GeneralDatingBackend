import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
os.chdir(Path(__file__).parent.parent / "src")

from fastapi.testclient import TestClient
from main import app
from core.security import create_access_token

needs_db = pytest.mark.skip(reason="Requires a live PostgreSQL database")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_access_token({"sub": "1"})
    return {"Authorization": f"Bearer {token}"}


class TestHealthCheck:
    def test_health_returns_ok(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_returns_app_name(self, client):
        response = client.get("/api/v1/health")
        data = response.json()
        assert "app" in data


class TestAuthEndpoints:
    @needs_db
    def test_send_otp_returns_success(self, client):
        response = client.post(
            "/api/v1/auth/send-otp",
            json={"phone_number": "9999999999"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "retry_after_seconds" in data

    def test_send_otp_empty_phone_rejected(self, client):
        response = client.post(
            "/api/v1/auth/send-otp",
            json={"phone_number": ""},
        )
        assert response.status_code == 422

    def test_send_otp_short_phone_rejected(self, client):
        response = client.post(
            "/api/v1/auth/send-otp",
            json={"phone_number": "123"},
        )
        assert response.status_code == 422

    @needs_db
    def test_verify_otp_invalid_returns_422(self, client):
        response = client.post(
            "/api/v1/auth/verify-otp",
            json={"phone_number": "9999999999", "otp": "000000"},
        )
        assert response.status_code == 422

    def test_verify_otp_missing_fields_returns_422(self, client):
        response = client.post(
            "/api/v1/auth/verify-otp",
            json={"phone_number": "9999999999"},
        )
        assert response.status_code == 422

    @needs_db
    def test_login_invalid_credentials(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"phone_number": "9999999999", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"phone_number": "9999999999"},
        )
        assert response.status_code == 422

    def test_refresh_without_token_returns_422(self, client):
        response = client.post("/api/v1/auth/refresh", json={})
        assert response.status_code == 422

    def test_refresh_with_invalid_token_returns_401(self, client):
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token"},
        )
        assert response.status_code == 401

    def test_unauthenticated_protected_endpoint(self, client):
        response = client.get("/api/v1/profile/me")
        assert response.status_code == 422

    def test_bad_auth_header_format(self, client):
        response = client.get(
            "/api/v1/profile/me",
            headers={"Authorization": "NotBearer token"},
        )
        assert response.status_code == 401


class TestProfileEndpoints:
    def test_setup_profile_requires_auth(self, client):
        response = client.post(
            "/api/v1/profile/setup",
            json={"name": "Test", "date_of_birth": "1995-01-01", "gender": "male", "city": "Mumbai"},
        )
        assert response.status_code == 422

    def test_get_profile_requires_auth(self, client):
        response = client.get("/api/v1/profile/me")
        assert response.status_code == 422


class TestDiscoveryEndpoints:
    def test_discovery_requires_auth(self, client):
        response = client.get("/api/v1/discovery")
        assert response.status_code == 422

    def test_swipe_requires_auth(self, client):
        response = client.post(
            "/api/v1/discovery/swipes",
            json={"swiped_id": 2, "direction": "like"},
        )
        assert response.status_code == 422


class TestAdminEndpoints:
    def test_dashboard_requires_auth(self, client):
        response = client.get("/api/v1/admin/dashboard")
        assert response.status_code == 422

    def test_users_requires_auth(self, client):
        response = client.get("/api/v1/admin/users")
        assert response.status_code == 422


class TestSubscriptionEndpoints:
    @needs_db
    def test_plans_are_public(self, client):
        response = client.get("/api/v1/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data

    def test_my_subscription_requires_auth(self, client):
        response = client.get("/api/v1/subscriptions/me")
        assert response.status_code == 422


class TestLandingPage:
    def test_landing_page(self, client):
        response = client.get("/")
        assert response.status_code in (200, 404)

    def test_subscribe_without_data_returns_422(self, client):
        response = client.post("/api/subscribe", json={})
        assert response.status_code == 422


class TestAdminStaticFiles:
    def test_admin_page(self, client):
        response = client.get("/admin")
        assert response.status_code in (200, 404)


class TestNotFound:
    def test_unknown_endpoint_returns_404(self, client):
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
