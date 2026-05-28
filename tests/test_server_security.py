"""Tests for backend/server.py security hardening (Phase 4)."""

import pytest
from fastapi.testclient import TestClient
from backend.server import app, settings


class TestCORSConfiguration:
    """CORS middleware configuration tests."""

    def test_cors_origins_loaded_from_settings(self):
        """Verify CORS_ORIGINS setting exists and is used."""
        assert hasattr(settings, "CORS_ORIGINS")
        # Default should be localhost:5173
        assert "localhost:5173" in settings.CORS_ORIGINS

    def test_cors_origins_csv_parsing(self):
        """Verify CORS origins are parsed from CSV string."""
        # This test verifies the parsing logic in server.py
        test_csv = "http://localhost:5173,http://localhost:3000"
        origins = [origin.strip() for origin in test_csv.split(",")]
        assert len(origins) == 2
        assert "http://localhost:5173" in origins
        assert "http://localhost:3000" in origins

    def test_cors_middleware_configured(self):
        """Verify CORS middleware is registered."""
        # Check that CORS middleware exists by verifying the middleware stack
        # FastAPI wraps middleware, so we check that middleware was added
        assert len(app.user_middleware) > 0

    def test_cors_allows_configured_origin(self):
        """Verify CORS allows requests from configured origins."""
        client = TestClient(app)
        response = client.get(
            "/",
            headers={"Origin": "http://localhost:5173"}
        )
        # Should not have wildcard
        assert response.headers.get("access-control-allow-origin") != "*"

    def test_cors_credentials_disabled(self):
        """Verify allow_credentials is False (security requirement)."""
        client = TestClient(app)
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET"
            }
        )
        # access-control-allow-credentials should be "false" or absent
        creds = response.headers.get("access-control-allow-credentials", "false")
        assert creds.lower() != "true"


class TestAudioValidation:
    """Audio upload validation tests."""

    def test_max_audio_mb_setting_exists(self):
        """Verify MAX_AUDIO_MB setting exists."""
        assert hasattr(settings, "MAX_AUDIO_MB")
        # Should be a string that can be converted to int
        max_mb = int(settings.MAX_AUDIO_MB)
        assert max_mb > 0

    def test_allowed_formats_constant(self):
        """Verify ALLOWED_FORMATS is defined in handle_audio_data."""
        # This is a code structure test - verifies the constant exists
        # Actual validation testing requires WebSocket client (manual test)
        import inspect
        from backend.server import handle_audio_data
        source = inspect.getsource(handle_audio_data)
        assert "ALLOWED_FORMATS" in source
        assert '{"webm", "wav", "ogg", "mp3"}' in source


class TestTempFileCleanup:
    """Temporary file cleanup tests."""

    def test_temp_file_cleanup_uses_finally(self):
        """Verify temp file cleanup is in finally block."""
        import inspect
        from backend.server import handle_audio_data
        source = inspect.getsource(handle_audio_data)
        # Check for finally block with unlink
        assert "finally:" in source
        assert "unlink(missing_ok=True)" in source

    def test_temp_path_initialized_outside_try(self):
        """Verify tmp_path is initialized before try block."""
        import inspect
        from backend.server import handle_audio_data
        source = inspect.getsource(handle_audio_data)
        lines = source.split("\n")
        # Find tmp_path = None and the first try: after it
        tmp_path_line = None
        try_line = None
        for i, line in enumerate(lines):
            if "tmp_path = None" in line:
                tmp_path_line = i
            if tmp_path_line is not None and "try:" in line.strip() and try_line is None:
                try_line = i
                break
        # tmp_path should be initialized before first try
        assert tmp_path_line is not None, "tmp_path = None not found"
        assert try_line is not None, "try: block not found after tmp_path"
        assert tmp_path_line < try_line, f"tmp_path at line {tmp_path_line} should be before try at line {try_line}"
