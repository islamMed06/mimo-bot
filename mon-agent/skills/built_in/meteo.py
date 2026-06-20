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
        mots_vides = {"quelle", "est", "la", "le", "de", "pour", "sur", "ce", "cette",
                      "donne", "donnemoi", "s'il", "te", "plait", "stp", "svp", "quel",
                      "meteo", "météo", "weather", "dans", "du", "a", "moi"}
        # priorite 1: mot apres "à" ou "a " ou "de " ou "pour "
        match = re.search(r'\b(?:à|a|de|pour|weather in)\s+(\w+)', texte, re.IGNORECASE)
        if match:
            ville = match.group(1).lower()
            if ville not in mots_vides:
                return ville.capitalize()
        # priorite 2: mot apres "meteo" ou "météo"
        match = re.search(r'\b(?:météo|meteo)\s+(\w+)', texte, re.IGNORECASE)
        if match:
            ville = match.group(1).lower()
            if ville not in mots_vides and len(ville) > 2:
                return ville.capitalize()
        # priorite 3: dernier mot significatif
        mots = [m.strip(",.!?") for m in texte.strip().split() if len(m.strip(",.!?")) > 2]
        for m in reversed(mots):
            if m.lower() not in mots_vides:
                return m.capitalize()
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
