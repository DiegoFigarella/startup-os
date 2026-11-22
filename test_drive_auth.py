import json
from types import SimpleNamespace

import sources


def test_drive_returns_none_without_configuration(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_FILE", raising=False)
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_FILE", raising=False)
    assert sources._drive_credentials() is None


def test_drive_oauth_uses_saved_token(monkeypatch, tmp_path) -> None:
    token_file = tmp_path / "drive-token.json"
    token_file.write_text(json.dumps({
        "token": "access", "refresh_token": "refresh", "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "client", "client_secret": "secret", "scopes": sources.DRIVE_SCOPES,
        "expiry": "2099-01-01T00:00:00Z",
    }))
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_FILE", str(tmp_path / "client.json"))
    monkeypatch.setenv("GOOGLE_OAUTH_TOKEN_FILE", str(token_file))

    credentials = sources._drive_credentials()

    assert credentials.refresh_token == "refresh"
    assert credentials.scopes == sources.DRIVE_SCOPES
