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
        for mot in ["a ", "à ", "de ", "sur ", "pour ", "météo ", "meteo ", "weather ", "in ", "at "]:
            if mot in texte.lower():
                parties = texte.lower().split(mot)
                if len(parties) > 1:
                    return parties[-1].split(" ")[0].strip()
        return "Alger"

    async def _meteo(self, ville):
        try:
            async with httpx.AsyncClient() as client:
                rep = await client.get(f"https://wttr.in/{ville}?format=%C|%t|%h|%w|%p", timeout=10)
                if rep.status_code == 200:
                    data = rep.text.strip().split("|")
                    if len(data) >= 3:
                        condition, temp, humidite = data[0], data[1], data[2]
                        vent = data[3] if len(data) > 3 else "N/A"
                        pluie = data[4] if len(data) > 4 else "0%"
                        return (
                            f"Météo à {ville.capitalize()} :\n"
                            f"Condition : {condition}\n"
                            f"Température : {temp}\n"
                            f"Humidité : {humidite}\n"
                            f"Vent : {vent}\n"
                            f"Précipitations : {pluie}"
                        )
                return f"Impossible de récupérer la météo pour {ville}."
        except Exception as e:
            log.warning(f"Erreur météo: {e}")
            return None
