from core.exceptions import (
    AppException, AuthException, ForbiddenException,
    NotFoundException, ConflictException, ValidationException,
    RateLimitException, PaymentRequiredException, VerificationRequiredException,
)


class TestExceptions:
    def test_auth_exception(self):
        exc = AuthException("Bad credentials")
        assert exc.status_code == 401
        assert exc.code == "auth_error"
        assert exc.detail == "Bad credentials"

    def test_auth_exception_default_message(self):
        exc = AuthException()
        assert exc.detail == "Authentication failed"

    def test_forbidden_exception(self):
        exc = ForbiddenException()
        assert exc.status_code == 403
        assert exc.code == "forbidden"

    def test_not_found_exception(self):
        exc = NotFoundException("User not found")
        assert exc.status_code == 404
        assert exc.code == "not_found"

    def test_conflict_exception(self):
        exc = ConflictException()
        assert exc.status_code == 409
        assert exc.code == "conflict"

    def test_validation_exception(self):
        exc = ValidationException("Invalid input")
        assert exc.status_code == 422
        assert exc.code == "validation_error"

    def test_rate_limit_exception(self):
        exc = RateLimitException(retry_after=30)
        assert exc.status_code == 429
        assert exc.code == "rate_limit"
        assert exc.headers["Retry-After"] == "30"

    def test_rate_limit_exception_default(self):
        exc = RateLimitException()
        assert exc.headers["Retry-After"] == "60"

    def test_payment_required_exception(self):
        exc = PaymentRequiredException()
        assert exc.status_code == 402
        assert exc.code == "payment_required"

    def test_verification_required_exception(self):
        exc = VerificationRequiredException()
        assert exc.status_code == 403
        assert exc.code == "verification_required"

    def test_all_exceptions_are_http_exceptions(self):
        from starlette.exceptions import HTTPException
        exceptions = [
            AuthException(), ForbiddenException(), NotFoundException(),
            ConflictException(), ValidationException(), RateLimitException(),
            PaymentRequiredException(), VerificationRequiredException(),
        ]
        for exc in exceptions:
            assert isinstance(exc, HTTPException)
