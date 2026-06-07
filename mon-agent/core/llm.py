import os
import json
import logging
from datetime import datetime, timezone, timedelta
from groq import Groq
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

ALGERIA_TZ = timezone(timedelta(hours=1))

def maintenant_algerie():
    return datetime.now(ALGERIA_TZ)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("LLM")

def detecter_langue(texte):
    import re
    mots_fr = len(re.findall(r'[àâçéèêëîïôûùüÿœæ]', texte))
    return "fr" if mots_fr > 0 else "en"

class LLMManager:
    def __init__(self, config):
        self.config = config
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
        self.gemini_disponible = bool(gemini_key)
        self.llm_actif = "groq"
        self.historique = []

    def get_system_prompt(self, user_message=None):
        maintenant = maintenant_algerie()
        aujourdhui = maintenant.strftime("%A %d %B %Y")
        jours_semaine_fr = {"Monday": "lundi", "Tuesday": "mardi", "Wednesday": "mercredi", "Thursday": "jeudi", "Friday": "vendredi", "Saturday": "samedi", "Sunday": "dimanche"}
        mois_fr = {"January": "janvier", "February": "février", "March": "mars", "April": "avril", "May": "mai", "June": "juin", "July": "juillet", "August": "août", "September": "septembre", "October": "octobre", "November": "novembre", "December": "décembre"}
        jour, mois, reste = aujourdhui.split(" ", 2)
        aujourdhui_fr = f"{jours_semaine_fr.get(jour, jour)} {mois_fr.get(mois, mois)} {reste}"
        heure = maintenant.strftime("%H:%M")
        langue = "fr"
        if user_message:
            langue = detecter_langue(user_message)
        base_fr = (
            f"Tu es {self.config['agent']['nom']}, un assistant AI personnel modulaire et autonome. "
            f"Nous sommes le {aujourdhui_fr} et il est {heure}. "
            f"Tu réponds toujours dans la langue de l'utilisateur. Sois concis, clair et utile. "
            f"Tu utilises Groq (llama-3.3-70b) comme LLM principal et Gemini (gemini-2.0-flash) en fallback. "
            f"Tu disposes d'outils pour la gestion du calendrier, des emails, des notes élèves, des fiches de leçons, "
            f"des statistiques, de la correction d'exercices et du contrôle du site web. "
            f"Tu confirmes toujours avant les actions sensibles (création, modification, envoi, installation). "
            f"Tu n'effectues jamais seul des actions de suppression en masse ou de partage de données privées."
        )
        base_en = (
            f"You are {self.config['agent']['nom']}, a modular and autonomous personal AI assistant. "
            f"Today is {aujourdhui} and the time is {heure}. "
            f"Always reply in the user's language. Be concise, clear, and helpful. "
            f"You use Groq (llama-3.3-70b) as your main LLM and Gemini (gemini-2.0-flash) as fallback. "
            f"You have tools for calendar management, emails, student grades, lesson plans, "
            f"statistics, exercise correction, and website control. "
            f"You always confirm before sensitive actions (create, modify, send, install). "
            f"You never perform mass deletions or private data sharing on your own."
        )
        return base_en if langue == "en" else base_fr

    def repondre(self, user_message):
        self.historique.append({"role": "user", "content": user_message})
        messages = [
            {"role": "system", "content": self.get_system_prompt(user_message)}
        ]
        for msg in self.historique[-self.config["memoire"]["court_terme_max_messages"]:]:
            messages.append(msg)
        texte = self._appeler_groq(messages)
        if texte is None:
            log.info("Groq indisponible, fallback vers Gemini")
            texte = self._appeler_gemini(messages)
            if texte:
                self.llm_actif = "gemini"
        else:
            self.llm_actif = "groq"
        if texte is None:
            texte = "Désolé, je ne peux pas répondre pour le moment (LLM indisponible)." if detecter_langue(user_message) == "fr" else "Sorry, I cannot answer right now (LLM unavailable)."
        self.historique.append({"role": "assistant", "content": texte})
        return texte, self.llm_actif

    def _appeler_groq(self, messages):
        try:
            completion = self.groq_client.chat.completions.create(
                model=self.config["llm"]["modele_groq"],
                messages=messages,
                max_tokens=self.config["llm"]["max_tokens"],
                temperature=self.config["llm"]["temperature"]
            )
            return completion.choices[0].message.content
        except Exception as e:
            log.warning(f"Erreur Groq: {e}")
            return None

    def _appeler_gemini(self, messages):
        try:
            system_msg = messages[0]["content"]
            user_msgs = [m["content"] for m in messages[1:]]
            prompt = f"{system_msg}\n\n" + "\n".join(user_msgs)
            model = genai.GenerativeModel(self.config["llm"]["modele_gemini"])
            reponse = model.generate_content(prompt)
            return reponse.text
        except Exception as e:
            log.warning(f"Erreur Gemini: {e}")
            return None
