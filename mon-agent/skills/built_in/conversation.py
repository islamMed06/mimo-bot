import logging

log = logging.getLogger("CONVERSATION")

class ConversationSkill:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory
        self.mode_actif = False

    async def executer(self, texte):
        texte_lower = texte.lower()

        if any(cmd in texte_lower for cmd in ["active le chat", "mode libre", "chat mode", "conversation libre"]):
            self.mode_actif = True
            return ("Mode conversation libre activé ! "
                    "Je suis plus détendu et créatif. "
                    "Dis 'desactive le chat' pour revenir au mode normal.")

        if any(cmd in texte_lower for cmd in ["desactive le chat", "mode normal", "normal mode", "stop chat"]):
            self.mode_actif = False
            return "Mode normal réactivé."

        if self.mode_actif:
            return None  # laisse le LLM gérer

        return None
