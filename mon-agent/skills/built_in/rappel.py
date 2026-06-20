import re
import logging
from datetime import datetime, timedelta, timezone
from core.llm import maintenant_algerie
from core.memory import ALGERIA_TZ

log = logging.getLogger("RAPPEL")

class RappelSkill:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory

    async def executer(self, texte, user_id=None):
        if not user_id:
            return "Erreur: utilisateur non identifie."
        self._user_id = user_id
        t = texte.lower()
        if "liste" in t or "list" in t or "affiche" in t or "mes rappels" in t:
            return self._liste()
        if "supprime" in t or "annule" in t or "efface" in t:
            return self._supprimer(texte)
        return await self._programmer(texte)

    async def _programmer(self, texte):
        duree_minutes = self._extraire_minutes(texte)
        if not duree_minutes:
            return ("Format : `programme un rappel dans X minutes/heures de [message]`\n"
                    "Ex : `programme un rappel dans 30 min de corriger les copies`")
        message = self._extraire_message(texte)
        if not message:
            return "Quel est le message du rappel ? (ex: `dans 30 min de [message]`)"
        echeance = maintenant_algerie() + timedelta(minutes=duree_minutes)
        doc_id = self.memory.ajouter_rappel(self._user_id, message, echeance.isoformat())
        if doc_id:
            return f"Rappel programmé dans {self._fmt_duree(duree_minutes)} (à {echeance.strftime('%H:%M')}) : {message}"
        return "Erreur lors de la programmation du rappel."

    def _extraire_minutes(self, texte):
        t = texte.lower()
        p = r"(\d+)\s*(min|minute|minutes|heure|heures|h|seconde|secondes|s)"
        m = re.search(p, t)
        if not m:
            return None
        val, unite = int(m.group(1)), m.group(2)
        if unite in ("heure", "heures", "h"):
            return val * 60
        if unite in ("min", "minute", "minutes"):
            return val
        return val // 60

    def _extraire_message(self, texte):
        for sep in [" de ", " pour ", " : ", ": "]:
            if sep in texte:
                return texte.split(sep, 1)[-1].strip()
        return ""

    def _fmt_duree(self, minutes):
        if minutes >= 60:
            h = minutes // 60
            m = minutes % 60
            return f"{h}h{m:02d}min" if m else f"{h}h"
        return f"{minutes}min"

    def _liste(self):
        rappels = self.memory.liste_rappels(self._user_id)
        if not rappels:
            return "Aucun rappel programmé."
        lignes = ["Rappels programmés :"]
        for rid, r in sorted(rappels.items()):
            ts = r.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts)
                aff = dt.strftime("%H:%M")
            except (ValueError, TypeError):
                aff = ts[:16]
            lignes.append(f"  `{rid[-6:]}` {aff} → {r['message'][:60]}")
        return "\n".join(lignes)

    def _supprimer(self, texte):
        rid = texte.strip().split()[-1]
        if rid.startswith("`"):
            rid = rid.strip("`")
        if len(rid) < 4:
            return "Usage : `supprime rappel X` où X est l'ID (ex: `supprime rappel a1b2c3`)"
        rappels = self.memory.liste_rappels(self._user_id)
        match = None
        for doc_id in rappels:
            if doc_id.endswith(rid) or rid in doc_id:
                match = doc_id
                break
        if not match:
            return f"Aucun rappel trouvé avec l'ID {rid}. Utilise `liste mes rappels` pour voir les IDs."
        if self.memory.supprimer_rappel(self._user_id, match):
            return f"Rappel `{rid}` supprimé."
        return "Erreur lors de la suppression."

    @staticmethod
    def get_function_schema():
        return {
            "type": "function",
            "function": {
                "name": "rappel",
                "description": "Programmer, lister ou supprimer des rappels",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["programmer", "lister", "supprimer"],
                            "description": "Action à effectuer"
                        },
                        "duree_minutes": {
                            "type": "integer",
                            "description": "Dans combien de minutes déclencher le rappel (pour programmer)"
                        },
                        "message": {
                            "type": "string",
                            "description": "Message du rappel (pour programmer)"
                        },
                        "id_suppression": {
                            "type": "string",
                            "description": "ID du rappel à supprimer (pour supprimer)"
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    async def executer_args(self, action, duree_minutes=None, message=None, id_suppression=None, user_id=None):
        if action == "lister":
            return await self.executer("liste mes rappels", user_id=user_id)
        if action == "supprimer":
            return await self.executer(f"supprime rappel {id_suppression}", user_id=user_id)
        if action == "programmer":
            texte = f"programme un rappel dans {duree_minutes} min"
            if message:
                texte += f" de {message}"
            return await self.executer(texte, user_id=user_id)
        return "Action non reconnue. Utilise programmer, lister ou supprimer."
