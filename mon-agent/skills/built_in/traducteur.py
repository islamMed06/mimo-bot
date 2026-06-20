import logging
import re
import httpx

log = logging.getLogger("TRADUCTEUR")

LANGUES = {
    "français": "fr", "francais": "fr", "french": "fr",
    "anglais": "en", "english": "en",
    "arabe": "ar", "arabic": "ar",
    "espagnol": "es", "spanish": "es",
    "allemand": "de", "german": "de",
    "italien": "it", "italian": "it",
    "turc": "tr", "turkish": "tr",
}

class TraducteurSkill:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory

    async def executer(self, texte):
        cible, source, texte_a_traduire = self._analyser(texte)
        if not texte_a_traduire:
            return "Usage : traduis 'bonjour' en anglais / translate 'hello' to french"
        return await self._traduire(texte_a_traduire, cible, source)

    def _analyser(self, texte):
        texte_lower = texte.lower()
        cible = "en"
        source = "auto"
        texte_a_traduire = ""

        # en/vers/à/to → langue cible
        for mot_clef in [" en ", " vers ", " à ", " to ", " into "]:
            if mot_clef in texte_lower:
                apres = texte_lower.split(mot_clef, 1)[1].strip()
                for nom, code in LANGUES.items():
                    if apres.startswith(nom):
                        cible = code
                        break

        # de/from → langue source
        for mot_clef in [" de ", " du ", " depuis ", " from "]:
            if mot_clef in texte_lower:
                apres = texte_lower.split(mot_clef, 1)[1].strip()
                for nom, code in LANGUES.items():
                    if apres.startswith(nom):
                        source = code
                        break

        # extraire le texte entre guillemets
        match = re.search(r"['\"](.+?)['\"]", texte)
        if match:
            texte_a_traduire = match.group(1)
        else:
            for cmd in ["traduis ", "traduit ", "translate "]:
                if cmd in texte_lower:
                    texte_a_traduire = texte[texte_lower.index(cmd) + len(cmd):].strip()
                    break

        return cible, source, texte_a_traduire

    async def _traduire(self, texte, cible, source):
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                params = {"q": texte, "target": cible}
                if source != "auto":
                    params["source"] = source
                rep = await client.post(
                    "https://libretranslate.com/translate",
                    json={"q": texte, "source": source, "target": cible},
                    timeout=15
                )
                if rep.status_code == 200:
                    resultat = rep.json()
                    return f"Traduction : {resultat.get('translatedText', texte)}"
                return f"Traduction ({source}→{cible}) : {texte}"
        except (httpx.RequestError, httpx.HTTPStatusError, KeyError):
            return f"Traduction ({source}→{cible}) : {texte}"

    @staticmethod
    def get_function_schema():
        return {
            "type": "function",
            "function": {
                "name": "traducteur",
                "description": "Traduire un texte d'une langue à une autre",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Texte à traduire"
                        },
                        "target_lang": {
                            "type": "string",
                            "description": "Langue cible (ex: français, anglais, arabe, espagnol)"
                        },
                        "source_lang": {
                            "type": "string",
                            "description": "Langue source (optionnel, auto-détection par défaut)"
                        }
                    },
                    "required": ["text", "target_lang"]
                }
            }
        }

    async def executer_args(self, text, target_lang="anglais", source_lang=None):
        lang_map = {
            "français": "fr", "francais": "fr", "french": "fr",
            "anglais": "en", "english": "en",
            "arabe": "ar", "arabic": "ar",
            "espagnol": "es", "spanish": "es",
            "allemand": "de", "german": "de",
            "italien": "it", "italian": "it",
            "turc": "tr", "turkish": "tr",
        }
        cible = lang_map.get(target_lang.lower(), "en")
        source = "auto"
        if source_lang:
            source = lang_map.get(source_lang.lower(), "auto")
        return await self._traduire(text, cible, source)
