import logging
from datetime import datetime, timedelta
log = logging.getLogger("CALENDRIER")

class CalendrierOutil:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory
        self.evenements = []

    async def executer(self, texte):
        texte_lower = texte.lower()
        if "ajoute" in texte_lower or "cree" in texte_lower or "nouveau" in texte_lower or "add" in texte_lower or "create" in texte_lower or "new" in texte_lower:
            return "Pour creer un evenement, donne-moi le titre, la date et l'heure. Je confirme avant d'ajouter."
        if "liste" in texte_lower or "voir" in texte_lower or "list" in texte_lower or "show" in texte_lower:
            return self.lister_aujourdhui()
        if "semaine" in texte_lower or "week" in texte_lower:
            return self.vue_semaine()
        if "mois" in texte_lower or "month" in texte_lower:
            return "Fonction vue du mois pas encore implementee."
        return "Calendrier: dis-moi ce que tu veux faire (lister, ajouter, voir semaine)."

    def lister_aujourdhui(self):
        aujourdhui = datetime.now().strftime("%d/%m/%Y")
        evenements = [e for e in self.evenements if e["date"] == aujourdhui]
        if not evenements:
            return f"Aucun evenement pour {aujourdhui}."
        lignes = [f"{e['heure']} - {e['titre']}" for e in evenements]
        return f"Evenements du {aujourdhui}:\n" + "\n".join(lignes)

    def vue_semaine(self):
        aujourdhui = datetime.now()
        debut = aujourdhui - timedelta(days=aujourdhui.weekday())
        return f"Semaine du {debut.strftime('%d/%m/%Y')}:\n(Fonction complete en developpement)"

    async def creer(self, titre, date, heure, description=""):
        return {"type": "confirmation", "action": "creer_evenement", "donnees": {"titre": titre, "date": date, "heure": heure, "description": description}}

    @staticmethod
    def get_function_schema():
        return {
            "type": "function",
            "function": {
                "name": "calendrier",
                "description": "Gérer le calendrier et les événements",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["lister", "semaine"],
                            "description": "Action à effectuer sur le calendrier"
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    async def executer_args(self, action="lister"):
        if action == "lister":
            return self.lister_aujourdhui()
        if action == "semaine":
            return self.vue_semaine()
        return "Calendrier: action non reconnue."
