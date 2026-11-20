"""Settings validation."""

import pytest
from pydantic import ValidationError

from penny.config import Settings


def test_a_settings_error_never_echoes_the_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PENNY_CACHE_KEY_SECRET", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-should-never-be-printed")
    with pytest.raises(ValidationError, match="cache_key_secret") as error:
        Settings()  # pyright: ignore[reportCallIssue]
    message = str(error.value)
    # Pydantic shortens long values to their first and last few characters.
    assert "input_value" not in message and "printed" not in message
