"""tests/conftest.py — shared fixtures"""
import pytest


@pytest.fixture
def mock_anthropic_client(monkeypatch):
    """Mock the Anthropic client to avoid real API calls in unit tests."""
    from unittest.mock import MagicMock, patch

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"items": []}')]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("shared.llm_client.get_client", return_value=mock_client):
        yield mock_client
