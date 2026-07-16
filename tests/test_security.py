from core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    generate_otp,
)


class TestPasswordHashing:
    def test_hash_returns_string(self):
        result = hash_password("test123")
        assert isinstance(result, str)
        assert result != "test123"

    def test_verify_correct_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_incorrect_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_hash_is_deterministic_for_verification(self):
        hashed = hash_password("same_password")
        assert verify_password("same_password", hashed) is True


class TestJWT:
    def test_create_access_token(self):
        token = create_access_token({"sub": "1"})
        assert isinstance(token, str)
        assert len(token) > 10

    def test_create_refresh_token(self):
        token = create_refresh_token({"sub": "1"})
        assert isinstance(token, str)

    def test_decode_valid_token(self):
        token = create_access_token({"sub": "42"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["type"] == "access"

    def test_decode_invalid_token(self):
        assert decode_token("invalid.token.here") is None

    def test_decode_empty_string(self):
        assert decode_token("") is None

    def test_refresh_token_has_refresh_type(self):
        token = create_refresh_token({"sub": "1"})
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_token_has_expiry(self):
        token = create_access_token({"sub": "1"})
        payload = decode_token(token)
        assert "exp" in payload


class TestOTP:
    def test_generate_otp_default_length(self):
        otp = generate_otp()
        assert isinstance(otp, str)
        assert len(otp) == 6
        assert otp.isdigit()

    def test_generate_otp_is_random(self):
        otps = {generate_otp() for _ in range(20)}
        assert len(otps) > 15
