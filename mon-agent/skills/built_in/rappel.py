import re
import logging
import threading
from datetime import datetime, timedelta

log = logging.getLogger("RAPPEL")

class RappelSkill:
    rappels = {}

    def __init__(self, config, memory):
        self.config = config
        self.memory = memory

    async def executer(self, texte):
        if "liste" in texte.lower() or "list" in texte.lower():
            return self._liste_rappels()
        if "supprime" in texte.lower() or "annule" in texte.lower() or "cancel" in texte.lower():
            return self._supprimer_dernier()
        return await self._programmer(texte)

    async def _programmer(self, texte):
        duree, unite = self._extraire_duree(texte)
        if not duree:
            return ("Usage : rappelle-moi dans X minutes/heures de ...\n"
                    "Ex : rappelle-moi dans 10 min de corriger les copies")

        message = self._extraire_message(texte)
        if not message:
            return "Quel est le message du rappel ?"

        secondes = self._en_secondes(duree, unite)
        heure = datetime.now() + timedelta(seconds=secondes)

        timer = threading.Timer(secondes, self._declencher, args=[message])
        timer.daemon = True
        timer.start()

        rappel_id = len(self.rappels) + 1
        self.rappels[rappel_id] = {"timer": timer, "message": message, "heure": heure}

        return f"Rappel programmé dans {duree} {unite} (à {heure.strftime('%H:%M')}) : {message}"

    def _extraire_duree(self, texte):
        pattern = r"(\d+)\s*(min|minute|minutes|heure|heures|h|seconde|secondes|s)"
        match = re.search(pattern, texte.lower())
        if match:
            return int(match.group(1)), match.group(2)
        return None, None

    def _extraire_message(self, texte):
        for sep in [" de ", " pour ", " : ", " :", ": "]:
            if sep in texte:
                return texte.split(sep, 1)[-1].strip()
        return ""

    def _en_secondes(self, duree, unite):
        if unite in ["min", "minute", "minutes"]:
            return duree * 60
        if unite in ["heure", "heures", "h"]:
            return duree * 3600
        if unite in ["seconde", "secondes", "s"]:
            return duree
        return duree * 60

    def _declencher(self, message):
        log.info(f"RAPPEL : {message}")

    def _liste_rappels(self):
        if not self.rappels:
            return "Aucun rappel programmé."
        lignes = ["Rappels programmés :"]
        for rid, r in self.rappels.items():
            lignes.append(f"- [{rid}] {r['heure'].strftime('%H:%M')} : {r['message']}")
        return "\n".join(lignes)

    def _supprimer_dernier(self):
        if not self.rappels:
            return "Aucun rappel à supprimer."
        rid = max(self.rappels.keys())
        self.rappels[rid]["timer"].cancel()
        del self.rappels[rid]
        return f"Rappel [{rid}] supprimé."
