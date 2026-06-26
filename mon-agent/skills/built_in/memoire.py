import logging
log = logging.getLogger("MEMOIRE_SKILL")

class MemoireSkill:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory

    async def executer(self, texte, user_id=None):
        profil = self.memory.charger_profil(user_id)
        identite = profil.get("identite", "Inconnue")
        prefs = profil.get("preferences", {})
        routines = profil.get("routine", {})
        habitudes = profil.get("habitudes", [])
        lignes = [f"Identité : {identite}"]
        if prefs:
            lignes.append(f"Préférences : {', '.join(f'{k}={v}' for k, v in prefs.items())}")
        if routines:
            lignes.append(f"Routine : {', '.join(f'{k}={v}' for k, v in routines.items())}")
        if habitudes:
            lignes.append(f"Habitudes : {', '.join(habitudes[-5:])}")
        return "Voici ce que je sais de toi:\n" + "\n".join(lignes)

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
        return await self.executer("", user_id=kwargs.get("user_id"))
