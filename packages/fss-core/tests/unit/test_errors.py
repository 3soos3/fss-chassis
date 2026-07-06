"""Unit tests for fss_core.errors module."""

from fss_core.errors import (
    AuthError,
    FSSCoreError,
    ExtensionError,
    IOLimitError,
    RateLimitError,
    SanitizationError,
    ValidationError,
)


class TestFSSCoreError:
    """Tests for FSSCoreError base class."""

    def test_has_correlation_id(self) -> None:
        err = FSSCoreError("test message", "TEST_CODE")
        assert hasattr(err, "correlation_id")
        assert len(err.correlation_id) == 12

    def test_correlation_id_is_hex(self) -> None:
        err = FSSCoreError("msg", "CODE")
        int(err.correlation_id, 16)  # Should not raise

    def test_has_code(self) -> None:
        err = FSSCoreError("msg", "MY_CODE")
        assert err.code == "MY_CODE"

    def test_str_includes_correlation_id(self) -> None:
        err = FSSCoreError("test message", "CODE")
        assert err.correlation_id in str(err)

    def test_unique_correlation_ids(self) -> None:
        err1 = FSSCoreError("msg", "C")
        err2 = FSSCoreError("msg", "C")
        assert err1.correlation_id != err2.correlation_id

    def test_is_exception(self) -> None:
        err = FSSCoreError("msg", "C")
        assert isinstance(err, Exception)


class TestValidationError:
    """Tests for ValidationError."""

    def test_default_code(self) -> None:
        err = ValidationError("bad input")
        assert err.code == "VALIDATION_ERROR"

    def test_custom_code(self) -> None:
        err = ValidationError("msg", "CUSTOM")
        assert err.code == "CUSTOM"

    def test_is_template_error(self) -> None:
        err = ValidationError("msg")
        assert isinstance(err, FSSCoreError)

    def test_message(self) -> None:
        err = ValidationError("field X is invalid")
        assert "field X is invalid" in str(err)


class TestSanitizationError:
    """Tests for SanitizationError."""

    def test_default_code(self) -> None:
        err = SanitizationError("bad input")
        assert err.code == "SANITIZATION_ERROR"

    def test_is_template_error(self) -> None:
        assert isinstance(SanitizationError("msg"), FSSCoreError)


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_default_code(self) -> None:
        err = RateLimitError("too fast")
        assert err.code == "RATE_LIMIT_EXCEEDED"

    def test_retry_after_default(self) -> None:
        err = RateLimitError("too fast")
        assert err.retry_after == 0.0

    def test_retry_after_custom(self) -> None:
        err = RateLimitError("too fast", retry_after=5.5)
        assert err.retry_after == 5.5

    def test_is_template_error(self) -> None:
        assert isinstance(RateLimitError("msg"), FSSCoreError)


class TestIOLimitError:
    """Tests for IOLimitError."""

    def test_default_code(self) -> None:
        err = IOLimitError("too big")
        assert err.code == "IO_LIMIT_EXCEEDED"

    def test_is_template_error(self) -> None:
        assert isinstance(IOLimitError("msg"), FSSCoreError)


class TestAuthError:
    """Tests for AuthError."""

    def test_default_code(self) -> None:
        err = AuthError("unauthorized")
        assert err.code == "AUTH_ERROR"

    def test_is_template_error(self) -> None:
        assert isinstance(AuthError("msg"), FSSCoreError)


class TestExtensionError:
    """Tests for ExtensionError."""

    def test_default_code(self) -> None:
        err = ExtensionError("load failed")
        assert err.code == "EXTENSION_ERROR"

    def test_is_template_error(self) -> None:
        assert isinstance(ExtensionError("msg"), FSSCoreError)
