import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

ALGERIA_TZ = timezone(timedelta(hours=1))
FIXED_NOW = datetime(2025, 6, 15, 10, 30, tzinfo=ALGERIA_TZ)

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test_groq_key")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("HF_API_KEY", "")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "")
    monkeypatch.setenv("GITHUB_TOKEN", "")
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", "")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
    monkeypatch.setenv("TELEGRAM_TOKEN", "test:token")

@pytest.fixture
def mock_now(monkeypatch):
    from core.llm import maintenant_algerie as real_now
    monkeypatch.setattr("core.llm.maintenant_algerie", lambda: FIXED_NOW)
    return FIXED_NOW

@pytest.fixture
def agent(mock_env_vars, monkeypatch):
    monkeypatch.setattr("core.llm.Groq", lambda api_key: MagicMock())
    from core.agent import Agent
    a = Agent()
    a.llm.repondre = MagicMock(return_value=("", "groq", None))
    a.llm.reformuler_avec_outil = MagicMock(return_value=("Reponse test", "groq"))
    return a
