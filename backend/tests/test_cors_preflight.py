"""CORS preflight for local and custom frontend origins."""

import pytest


@pytest.mark.parametrize(
    "path",
    ["/auth/refresh", "/auth/logout"],
)
def test_preflight_allows_local_vite_origin_and_custom_headers(client, path):
    res = client.options(
        path,
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-requested-with, x-csrf-token, content-type, authorization",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
    allowed = (res.headers.get("access-control-allow-headers") or "").lower()
    assert "x-requested-with" in allowed or allowed == "*"
    assert "x-csrf-token" in allowed or allowed == "*"


def test_production_cors_regex_allows_firebase_style_hosts(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)
    monkeypatch.setenv("STORAGE_PROVIDER", "s3")
    monkeypatch.setenv("S3_BUCKET", "bharathi-test-bucket")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://u:p@db.example.com:5432/bharathi_erp",
    )
    s = Settings(_env_file=None)
    assert s.is_production
    assert s.cors_origin_allowed_by_regex("https://bharathi-example.web.app")