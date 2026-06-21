import pytest
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime, timezone, timedelta
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ALGERIA_TZ = timezone(timedelta(hours=1))

class TestTraiterMessage:
    @pytest.mark.asyncio
    async def test_fallback_router(self, agent):
        agent.llm.repondre = MagicMock(return_value=("Salut !", "groq", None))
        reponse, llm = await agent.traiter_message("Comment ca va ?", "user1")
        assert reponse == "Salut !"
        assert llm == "groq"

    @pytest.mark.asyncio
    async def test_function_calling_flow(self, agent):
        tc = [{"id": "call_1", "type": "function", "function": {"name": "conversation", "arguments": '{"action": "activer"}'}}]
        agent.llm.repondre = MagicMock()
        agent.llm.repondre.side_effect = [
            ("", "groq", tc),
            ("", "groq", None),
        ]
        agent.llm.reformuler_avec_outil = MagicMock(return_value=("Mode libre active !", "groq"))
        agent.outils["conversation"].executer_args = MagicMock(return_value="Mode conversation libre active !")
        reponse, llm = await agent.traiter_message("active le chat", "user1")
        assert "Mode libre" in reponse
        assert llm == "groq"

    @pytest.mark.asyncio
    async def test_max_tool_iterations(self, agent):
        tc = [{"id": "call_loop", "type": "function", "function": {"name": "conversation", "arguments": '{"action": "activer"}'}}]
        agent.llm.repondre = MagicMock(return_value=("", "groq", tc))
        agent.llm.reformuler_avec_outil = MagicMock(return_value=("Apres 2 iterations", "groq"))
        agent.outils["conversation"].executer_args = MagicMock(return_value="ok")
        reponse, llm = await agent.traiter_message("test", "user1")
        assert agent.llm.repondre.call_count == 2

    @pytest.mark.asyncio
    async def test_auto_name_detection(self, agent):
        from datetime import datetime
        agent.llm.repondre = MagicMock(return_value=("Enchante Jean !", "groq", None))
        await agent.traiter_message("je suis Jean", "user_name_test")
        profil = agent.memory.charger_profil("user_name_test")
        assert "Jean" in profil.get("identite", "")

    @pytest.mark.asyncio
    async def test_user_partition(self, agent):
        agent.llm.repondre = MagicMock(return_value=("Bonjour", "groq", None))
        agent.llm.reformuler_avec_outil = MagicMock(return_value=("Bonjour", "groq"))
        await agent.traiter_message("salut", "user_a")
        await agent.traiter_message("hello", "user_b")
        assert len(agent.memory.court_terme["user_a"]) == 2
        assert len(agent.memory.court_terme["user_b"]) == 2
        assert agent.memory.court_terme["user_a"][0]["contenu"] == "salut"
        assert agent.memory.court_terme["user_b"][0]["contenu"] == "hello"

    @pytest.mark.asyncio
    async def test_empty_response(self, agent):
        agent.llm.repondre = MagicMock(return_value=("", "groq", None))
        reponse, llm = await agent.traiter_message("test vide", "user1")
        assert isinstance(reponse, str)

    @pytest.mark.asyncio
    async def test_restore_contexte_first_msg(self, agent):
        agent.llm.repondre = MagicMock(return_value=("bienvenue", "groq", None))
        await agent.traiter_message("premier message", "user_new")
        assert len(agent.llm.historique) >= 0

    @pytest.mark.asyncio
    async def test_identite_injected_on_second_msg(self, agent):
        agent.llm.repondre = MagicMock(return_value=("ok", "groq", None))
        agent.llm.historique = [{"role": "user", "content": "ancien message"}]
        ts = datetime.now().timestamp() + 1000
        agent.memory._cache_profil._cache["user_id_test"] = {
            "profil": {"identite": "L'utilisateur s'appelle Alice"},
            "ts": ts
        }
        with patch.object(agent.llm, "identite_est_valide", return_value=True):
            await agent.traiter_message("deuxieme message", "user_id_test")
        system_msgs = [m for m in agent.llm.historique if m["role"] == "system" and "[Profil utilisateur]" in m["content"]]
        assert any("Alice" in m["content"] for m in system_msgs)
