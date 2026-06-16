import logging
log = logging.getLogger("MEMOIRE_SKILL")

class MemoireSkill:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory

    async def executer(self, texte):
        return "Voici ce que je sais de toi:\n" + self.memory.get_contexte()
