import logging
import httpx

log = logging.getLogger("RECHERCHE_WEB")

class RechercheWebSkill:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory

    async def executer(self, texte, user_id=None):
        if "cherche" in texte.lower() or "recherche" in texte.lower() or "search" in texte.lower():
            query = texte.replace("cherche", "").replace("recherche", "").replace("search", "").strip()
            if query:
                return await self.rechercher(query)
            return "Qu'est-ce que tu veux que je cherche ?"
        if "difference" in texte.lower() or "difference" in texte.lower():
            return await self._repondre_via_llm(texte)
        return await self._repondre_via_llm(texte)

    async def _repondre_via_llm(self, texte):
        return None

    async def rechercher(self, query):
        try:
            async with httpx.AsyncClient() as client:
                rep = await client.get(
                    f"https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
                    timeout=10
                )
                if rep.status_code == 200:
                    data = rep.json()
                    abstract = data.get("Abstract", "")
                    if abstract:
                        return f"Resultat de recherche pour '{query}':\n{abstract}"
                    return f"Je n'ai pas trouve de resultat precis pour '{query}'."
                return f"Erreur recherche pour '{query}'."
        except Exception as e:
            log.warning(f"Erreur recherche web: {e}")
            return None

    @staticmethod
    def get_function_schema():
        return {
            "type": "function",
            "function": {
                "name": "recherche_web",
                "description": "Effectuer une recherche sur Internet",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Termes de recherche"
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    async def executer_args(self, query, **kwargs):
        return await self.rechercher(query)
