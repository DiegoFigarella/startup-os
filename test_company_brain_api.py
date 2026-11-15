import os

import pytest
from fastapi import HTTPException

from company_brain.app import require_key


def test_api_key_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANY_BRAIN_API_KEY", "local-key")
    with pytest.raises(HTTPException, match="invalid API key"):
        require_key(None)


def test_api_key_accepts_exact_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANY_BRAIN_API_KEY", "local-key")
    require_key("local-key")
