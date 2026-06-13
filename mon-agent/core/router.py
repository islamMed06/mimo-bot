import re
import logging

log = logging.getLogger("ROUTER")

MOTS_CLEFS = {
    "calendrier": ["calendrier", "agenda", "evenement", "rendez-vous", "semaine", "mois", "planning", "schedule", "calendar", "event", "reminder"],
    "email": ["email", "mail", "courriel", "boite mail", "boîte mail", "boite reception", "boîte réception", "envoyer email", "envoyer mail", "lire email", "lire mail", "lire mes emails", "lire mes mails"],
    "correction": ["corrige", "correction", "corriger", "feuille", "exercice", "devoir", "correction", "correct", "exercise"],
    "notes": ["note", "eleve", "moyenne", "classe", "note", "student", "grade", "average"],
    "fiches": ["fiche", "lecon", "cours", "exercice", "examen", "sujet", "lesson", "worksheet"],
    "stats": ["statistique", "graphique", "progression", "rapport", "moyenne", "classe", "stats", "chart", "graph"],
    "site_web": ["site", "utilisateur", "inscrit", "premium", "upload", "fichier", "dossier", "website", "user", "file"],
    "recherche": ["cherche", "recherche", "google", "internet", "actualite", "info", "qu-est-ce que", "search", "what is", "difference entre"],
    "installation": ["installe", "installer", "ajoute outil", "nouvel outil", "mcp", "package", "dependance", "tool"],
    "meteo": ["meteo", "météo", "weather", "wttr"],
    "traduction": ["traduis", "traduit", "traduction", "translate", "translation"],
    "rappel": ["rappel", "rappelle", "rappeler", "remind", "reminder", "dans 1", "dans 2", "dans 3", "dans 5", "dans 10", "dans 15", "dans 30"],
    "conversation": ["mode libre", "mode chat", "chat mode", "conversation", "active le chat", "desactive le chat"]
}

EXCLUSIONS = {
    "rappel": [r'\btu te rappelles?\b', r'\bvous (vous )?rappelles?\b', r'\bse rappelle\b', r'\bse souvenir\b', r'\bte souviens.tu\b', r'\ben rappelle\b']
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
    if intention == "calendrier":
        return outils.get("calendrier", None)
    elif intention == "email":
        return outils.get("email", None)
    elif intention == "correction":
        return outils.get("correction", None)
    elif intention == "notes":
        return outils.get("notes", None)
    elif intention == "fiches":
        return outils.get("fiches", None)
    elif intention == "stats":
        return outils.get("stats", None)
    elif intention == "site_web":
        return outils.get("site_web", None)
    elif intention == "recherche":
        return outils.get("recherche_web", None)
    elif intention == "installation":
        return outils.get("auto_install", None)
    elif intention == "meteo":
        return outils.get("meteo", None)
    elif intention == "traduction":
        return outils.get("traducteur", None)
    elif intention == "rappel":
        return outils.get("rappel", None)
    elif intention == "conversation":
        return outils.get("conversation", None)
    return None
