import os
import logging
import httpx

log = logging.getLogger("SITE_WEB")

class SiteWebOutil:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory
        self.site_url = os.getenv("SITE_URL", "http://localhost:3000")
        self.api_secret = os.getenv("SITE_API_SECRET", "")

    async def executer(self, texte):
        texte_lower = texte.lower()
        if "utilisateur" in texte_lower or "user" in texte_lower:
            if "liste" in texte_lower or "list" in texte_lower or "voir" in texte_lower or "show" in texte_lower:
                return await self._api_call("GET", "/api/agent/users/list")
            if "ajoute" in texte_lower or "add" in texte_lower:
                return "Pour ajouter un utilisateur, donne-moi son email et son nom. Je confirme avant."
            if "premium" in texte_lower or "activer" in texte_lower or "activate" in texte_lower:
                return "Pour activer premium, donne-moi l'email de l'utilisateur. Je confirme avant."
            if "supprime" in texte_lower or "remove" in texte_lower or "delete" in texte_lower:
                return "Je ne peux pas supprimer d'utilisateur sans confirmation explicite."
        if "fichier" in texte_lower or "file" in texte_lower or "upload" in texte_lower:
            return "Pour uploader un fichier, envoie-moi le fichier et le dossier de destination."
        if "stat" in texte_lower or "inscrit" in texte_lower:
            return await self._api_call("GET", "/api/agent/stats")
        return "Site web: dis-moi ce que tu veux gerer (utilisateurs, fichiers, stats)."

    async def _api_call(self, methode, chemin, donnees=None):
        try:
            url = f"{self.site_url}{chemin}"
            headers = {"X-Agent-Secret": self.api_secret}
            async with httpx.AsyncClient() as client:
                if methode == "GET":
                    rep = await client.get(url, headers=headers)
                else:
                    rep = await client.post(url, headers=headers, json=donnees or {})
                if rep.status_code == 200:
                    return f"Reponse du site: {rep.json()}"
                return f"Erreur site ({rep.status_code}): {rep.text}"
        except Exception as e:
            return f"Impossible de contacter le site: {e}"

    @staticmethod
    def get_function_schema():
        return {
            "type": "function",
            "function": {
                "name": "site_web",
                "description": "Interagir avec le site web (utilisateurs, statistiques)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["liste_utilisateurs", "stats", "ajouter_utilisateur"],
                            "description": "Action à effectuer"
                        },
                        "email": {
                            "type": "string",
                            "description": "Email de l'utilisateur"
                        },
                        "nom": {
                            "type": "string",
                            "description": "Nom de l'utilisateur"
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    async def executer_args(self, action, email=None, nom=None):
        if action == "liste_utilisateurs":
            return await self._api_call("GET", "/api/agent/users/list")
        if action == "stats":
            return await self._api_call("GET", "/api/agent/stats")
        if action == "ajouter_utilisateur":
            return "Pour ajouter un utilisateur, donne-moi son email et son nom. Je confirme avant."
        return "Site web: action non reconnue."
