import pytest
from unittest.mock import MagicMock, patch
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Fake Groq completion helpers
class FakeMsg:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

class FakeChoice:
    def __init__(self, msg):
        self.message = msg

class FakeCompletion:
    def __init__(self, msg):
        self.choices = [FakeChoice(msg)]

class FakeToolCall:
    def __init__(self, name="meteo", args='{"ville": "Alger"}'):
        self.id = "call_test_123"
        self.type = "function"
        self.function = type("FakeFn", (), {"name": name, "arguments": args})()

CONFIG = {
    "agent": {"nom": "MimoBot", "version": "test"},
    "llm": {"modele_groq": "test-model", "max_tokens": 1024, "temperature": 0.7,
            "modele_gemini": "gemini-2.0-flash", "modele_openrouter": "test-model",
            "modele_huggingface": "test-model", "modele_cloudflare": "test-model",
            "modele_github": "test-model"},
    "memoire": {"court_terme_max_messages": 20}
}

@pytest.fixture
def llm(mock_env_vars, mock_now, monkeypatch):
    from core.llm import LLMManager
    mock_client = MagicMock()
    monkeypatch.setattr("core.llm.Groq", lambda api_key: mock_client)
    manager = LLMManager(CONFIG)
    return manager, mock_client

class TestLLMManager:
    def test_time_query_bypass(self, llm):
        manager, _ = llm
        texte, llm_nom, tc = manager.repondre("quelle heure")
        assert tc is None
        assert llm_nom == "system"
        assert "10:30" in texte
        assert "15/06/2025" in texte

    def test_tool_calls_formatted(self, llm):
        manager, mock_client = llm
        tc = [FakeToolCall("conversation", '{"action": "activer"}')]
        mock_client.chat.completions.create.return_value = FakeCompletion(FakeMsg(content="", tool_calls=tc))
        texte, llm_nom, tc_list = manager.repondre("active le chat", tools=[{"type": "function", "function": {"name": "conversation"}}])
        assert tc_list is not None
        assert len(tc_list) == 1
        assert tc_list[0]["function"]["name"] == "conversation"
        assert tc_list[0]["type"] == "function"

    def test_empty_content_fallback(self, llm):
        manager, mock_client = llm
        mock_client.chat.completions.create.return_value = FakeCompletion(FakeMsg(content=None))
        with patch.object(manager, "_fallback_chain", return_value="fallback ok"):
            texte, llm_nom, tc = manager.repondre("bonjour")
            assert texte == "fallback ok"
            assert tc is None

    def test_fallback_chain_priorities(self, llm):
        manager, mock_client = llm
        mock_client.chat.completions.create.return_value = FakeCompletion(FakeMsg(content=None))
        from core.llm import _fetch_http_time
        with patch.object(manager, "_appeler_gemini", return_value=None):
            with patch("core.llm.os.getenv", side_effect=lambda k, d=None: {"GROQ_API_KEY": "test", "GEMINI_API_KEY": "test", "TELEGRAM_TOKEN": "test:token"}.get(k, "")):
                texte, llm_nom, tc = manager.repondre("salut")
                assert tc is None
                assert "LLM" in texte or "indisponible" in texte or "unavailable" in texte or "erreur" in texte.lower()

    def test_system_prompt(self, llm, mock_now):
        manager, _ = llm
        prompt = manager.get_system_prompt("bonjour")
        assert "MimoBot" in prompt
        assert "assistant" in prompt

    def test_resume_anciens(self, llm):
        manager, mock_client = llm
        fake_resume = FakeCompletion(FakeMsg(content="Resume: conversation de test"))
        fake_identite = FakeCompletion(FakeMsg(content="L'utilisateur s'appelle Test"))
        mock_client.chat.completions.create.side_effect = [fake_resume, fake_identite]
        from unittest.mock import MagicMock
        mock_memory = MagicMock()
        mock_memory.charger_profil.return_value = {}
        mock_memory.sauvegarder_resume = MagicMock()
        mock_memory.sauvegarder_profil = MagicMock()
        manager.memory = mock_memory
        for i in range(42):
            manager.historique.append({"role": "user", "content": f"message {i}"})
        manager.repondre("dernier message", user_id="test")
        mock_memory.sauvegarder_resume.assert_called_once()
        assert len(manager.historique) <= 25
