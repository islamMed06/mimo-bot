import logging
log = logging.getLogger("CORRECTION")

class CorrectionOutil:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory

    async def executer(self, texte):
        if "corrige" in texte.lower() or "correct" in texte.lower():
            return "Envoie-moi le fichier (image ou PDF) de la feuille d'exercices a corriger."
        if "generer" in texte.lower() or "generate" in texte.lower():
            return "Donne-moi le sujet de l'exercice pour lequel generer un corrige type."
        return "Correction: envoie-moi une feuille d'exercices a corriger ou demande-moi de generer un corrige."

    async def corriger_feuille(self, chemin_fichier):
        return {"type": "analyse", "message": f"Analyse du fichier {chemin_fichier} en cours..."}

    @staticmethod
    def get_function_schema():
        return {
            "type": "function",
            "function": {
                "name": "correction",
                "description": "Corriger des exercices ou générer un corrigé type",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["corriger", "generer_corrige"],
                            "description": "Action à effectuer"
                        },
                        "sujet": {
                            "type": "string",
                            "description": "Sujet de l'exercice (pour générer un corrigé)"
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    async def executer_args(self, action, sujet=None):
        return await self.executer(f"{action} {sujet or ''}")
