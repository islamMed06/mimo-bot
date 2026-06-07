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
