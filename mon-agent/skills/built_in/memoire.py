import logging
log = logging.getLogger("MEMOIRE_SKILL")

class MemoireSkill:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory

    async def executer(self, texte, user_id=None):
        return "Voici ce que je sais de toi:\n" + self.memory.get_contexte()

    @staticmethod
    def get_function_schema():
        return {
            "type": "function",
            "function": {
                "name": "memoire",
                "description": "Afficher les informations connues sur l'utilisateur (profil, identité)",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }

    async def executer_args(self, **kwargs):
        return await self.executer("")
