import logging
log = logging.getLogger("NOTES")

class NotesOutil:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory

    async def executer(self, texte):
        texte_lower = texte.lower()
        if "moyenne" in texte_lower or "average" in texte_lower:
            return "Pour calculer une moyenne, donne-moi la classe ou le nom de l'eleve."
        if "ajoute" in texte_lower or "add" in texte_lower:
            return "Donne-moi le nom de l'eleve, la matiere et la note a ajouter. Je confirme avant."
        if "liste" in texte_lower or "list" in texte_lower or "voir" in texte_lower or "show" in texte_lower:
            return "Pour voir les notes, precise la classe ou le nom de l'eleve."
        return "Notes: dis-moi ce que tu veux faire (lister, ajouter, moyenne)."

    @staticmethod
    def get_function_schema():
        return {
            "type": "function",
            "function": {
                "name": "notes",
                "description": "Gérer les notes des élèves (lister, ajouter, calculer moyenne)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["lister", "ajouter", "moyenne"],
                            "description": "Action à effectuer"
                        },
                        "eleve": {
                            "type": "string",
                            "description": "Nom de l'élève"
                        },
                        "matiere": {
                            "type": "string",
                            "description": "Matière"
                        },
                        "note": {
                            "type": "number",
                            "description": "Note sur 20"
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    async def executer_args(self, action, eleve=None, matiere=None, note=None):
        return await self.executer(f"{action} {eleve or ''} {matiere or ''}".strip())
