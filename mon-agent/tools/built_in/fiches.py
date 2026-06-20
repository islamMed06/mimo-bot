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

    @staticmethod
    def get_function_schema():
        return {
            "type": "function",
            "function": {
                "name": "fiches",
                "description": "Générer des fiches de leçon, exercices ou examens",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["fiche", "exercice", "examen"],
                            "description": "Type de contenu à générer"
                        },
                        "sujet": {
                            "type": "string",
                            "description": "Sujet de la leçon ou de l'exercice"
                        },
                        "niveau": {
                            "type": "string",
                            "description": "Niveau (A1, A2, B1, B2, C1)"
                        },
                        "duree": {
                            "type": "string",
                            "description": "Durée de la leçon ou de l'examen"
                        }
                    },
                    "required": ["action", "sujet"]
                }
            }
        }

    async def executer_args(self, action, sujet, niveau=None, duree=None):
        return await self.executer(f"{action} {sujet} {niveau or ''} {duree or ''}".strip())
        if "fiche" in t or "lecon" in t or "lesson" in t:
            return "Donne-moi le sujet, le niveau (A1, A2, B1...) et la duree de la lecon."
        if "exercice" in t or "exercise" in t:
            return "Donne-moi le sujet, le niveau et le nombre d'exercices souhaites."
        if "examen" in t or "exam" in t or "sujet" in t:
            return "Donne-moi le sujet, le niveau et la duree de l'examen."
        return None
