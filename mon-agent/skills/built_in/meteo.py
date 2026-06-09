import re
import logging
import httpx

log = logging.getLogger("METEO")

class MeteoSkill:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory

    async def executer(self, texte):
        ville = self._extraire_ville(texte)
        return await self._meteo(ville)

    def _extraire_ville(self, texte):
        # priorite 1: "à/météo weather in <Ville>"
        match = re.search(r'(?:à|a |météo|meteo|weather in|de |pour )\s*(\w+)', texte, re.IGNORECASE)
        if match:
            ville = match.group(1).lower()
            if ville not in ["quelle", "est", "la", "le", "de", "pour", "sur", "ce", "cette", "donne", "donne-moi", "s'il", "te", "plait", "s'il te plaît", "stp", "svp", "quel"]:
                return ville.capitalize()
        # priorite 2: dernier mot du texte si court
        mots = texte.strip().split()
        if len(mots) <= 4:
            for m in reversed(mots):
                m_clean = m.strip(",.!?")
                if m_clean.lower() not in ["météo", "meteo", "weather", "donne", "moi", "la", "le", "de", "du", "à", "a", "s'il", "te", "plait", "stp", "svp"] and len(m_clean) > 2:
                    return m_clean.capitalize()
        return "Alger"

    async def _meteo(self, ville):
        try:
            async with httpx.AsyncClient() as client:
                rep = await client.get(f"https://wttr.in/{ville}?format=%C|%t|%h|%w|%p&m", timeout=10)
                if rep.status_code == 200:
                    data = rep.text.strip().split("|")
                    if len(data) >= 3:
                        condition, temp, humidite = data[0], data[1], data[2]
                        vent = data[3] if len(data) > 3 else "N/A"
                        pluie = data[4] if len(data) > 4 else "0%"
                        condition = condition.replace("Partly cloudy", "Partiellement nuageux") \
                            .replace("Sunny", "Ensoleillé") \
                            .replace("Clear", "Dégagé") \
                            .replace("Cloudy", "Nuageux") \
                            .replace("Overcast", "Couvert") \
                            .replace("Light rain", "Pluie légère") \
                            .replace("Heavy rain", "Pluie forte") \
                            .replace("Rain", "Pluie") \
                            .replace("Mist", "Brume") \
                            .replace("Fog", "Brouillard") \
                            .replace("Snow", "Neige") \
                            .replace("Thunderstorm", "Orage") \
                            .replace("Drizzle", "Crachin")
                        return (
                            f"Météo à {ville.capitalize()} :\n"
                            f"Condition : {condition}\n"
                            f"Température : {temp}\n"
                            f"Humidité : {humidite}\n"
                            f"Vent : {vent}\n"
                            f"Précipitations : {pluie}"
                        )
                return f"Je n'ai pas pu récupérer la météo pour {ville}."
        except Exception as e:
            log.warning(f"Erreur météo: {e}")
            return None
