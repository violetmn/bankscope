"""Tests are offline, even if a developer has a real key in their environment."""
import pytest


@pytest.fixture(autouse=True)
def no_accidental_paid_calls(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('BANKSCOPE_ENABLE_PAID', raising=False)

    def blocked(*args, **kwargs):
        raise AssertionError('Unexpected network call: tests must mock external providers')

    monkeypatch.setattr('urllib.request.urlopen', blocked)
