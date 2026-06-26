import re
import logging

log = logging.getLogger("ROUTER")

MOTS_CLEFS = {
    "site_web": ["site web", "utilisateur", "inscrit"],
    "recherche": ["cherche sur internet", "recherche google", "actualite", "search internet", "what is"],
    "meteo": ["meteo", "météo", "weather", "wttr", "temperature", "température", "degré"],
    "traduction": ["traduis", "traduit", "traduction", "translate"],
    "rappel": ["programme un rappel", "ajoute un rappel", "rappelle-moi", "rappelle moi", "crée un rappel", "liste mes rappels", "supprime rappel", "affiche mes rappels"],
    "conversation": []
}

EXCLUSIONS = {
    "rappel": [r'\btu te rappelles?\b', r'\bvous (vous )?rappelles?\b', r'\bse rappelle\b', r'\bse souvenir\b', r'\bte souviens.tu\b', r'\ben rappelle\b', r'\bje me rappelle\b', r'\bne .* rappelle pas\b'],
}

def detecter_intention(texte):
    texte_lower = texte.lower()
    scores = {}
    for intention, mots in MOTS_CLEFS.items():
        if intention in EXCLUSIONS and any(re.search(p, texte_lower) for p in EXCLUSIONS[intention]):
            continue
        score = 0
        for mot in mots:
            if mot in texte_lower:
                score += 1
        if score > 0:
            scores[intention] = score
    if not scores:
        return "conversation"
    intention_principale = max(scores, key=scores.get)
    return intention_principale

def executer_intention(intention, texte, outils):
    mapping = {
        "site_web": "site_web",
        "recherche": "recherche_web",
        "meteo": "meteo",
        "traduction": "traducteur",
        "rappel": "rappel",
        "conversation": "conversation",
    }
    nom_outil = mapping.get(intention)
    if nom_outil:
        return outils.get(nom_outil, None)
    return None
