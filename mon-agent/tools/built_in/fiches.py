import re
import logging
log = logging.getLogger("FICHES")

class FichesOutil:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory

    async def executer(self, texte):
        t = texte.lower().strip()
        # Si c'est une question generale ou hypothetique → laisser le LLM repondre
        if re.search(r'\b(si|est-ce que|peux.tu|peut.tu|es.tu|vas.tu|qu-est-ce)\b', t) and '?' in t:
            return None
        if "fiche" in t or "lecon" in t or "lesson" in t:
            return "Donne-moi le sujet, le niveau (A1, A2, B1...) et la duree de la lecon."
        if "exercice" in t or "exercise" in t:
            return "Donne-moi le sujet, le niveau et le nombre d'exercices souhaites."
        if "examen" in t or "exam" in t or "sujet" in t:
            return "Donne-moi le sujet, le niveau et la duree de l'examen."
        return None
