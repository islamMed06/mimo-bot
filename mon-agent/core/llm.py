import os
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from groq import Groq, RateLimitError
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
    def __init__(self, config, memory=None):
        self.config = config
        self.memory = memory
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
        self.gemini_disponible = bool(gemini_key)
        self.llm_actif = "groq"
        self.historique = []
        self.derniere_erreur_groq = ""
        self.derniere_erreur_gemini = ""

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
            f"Tu utilises Groq (llama-3.1-8b) comme LLM principal et Gemini (gemini-2.0-flash) en fallback. "
            f"Tu disposes d'outils pour la gestion du calendrier, des emails, des notes élèves, des fiches de leçons, "
            f"des statistiques, de la correction d'exercices et du contrôle du site web. "
            f"Tu confirmes toujours avant les actions sensibles (création, modification, envoi, installation). "
            f"Tu n'effectues jamais seul des actions de suppression en masse ou de partage de données privées."
        )
        base_en = (
            f"You are {self.config['agent']['nom']}, a modular and autonomous personal AI assistant. "
            f"Today is {aujourdhui} and the time is {heure}. "
            f"Always reply in the user's language. Be concise, clear, and helpful. "
            f"You use Groq (llama-3.1-8b) as your main LLM and Gemini (gemini-2.0-flash) as fallback. "
            f"You have tools for calendar management, emails, student grades, lesson plans, "
            f"statistics, exercise correction, and website control. "
            f"You always confirm before sensitive actions (create, modify, send, install). "
            f"You never perform mass deletions or private data sharing on your own."
        )
        return base_en if langue == "en" else base_fr

    def _resumer_anciens(self):
        anciens = self.historique[:-self.config["memoire"]["court_terme_max_messages"]]
        if len(anciens) > 5:
            texte = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in anciens])
            try:
                completion = self.groq_client.chat.completions.create(
                    model=self.config["llm"]["modele_groq"],
                    messages=[{"role": "system", "content": "Resume cette conversation en 2-3 phrases, en francais."},
                              {"role": "user", "content": texte}],
                    max_tokens=200
                )
                resume = completion.choices[0].message.content
                if self.memory:
                    self.memory.sauvegarder_resume(resume)
                self.historique = self.historique[-self.config["memoire"]["court_terme_max_messages"]:]
                self.historique.insert(0, {"role": "system", "content": f"[Resume conversation precedente] {resume}"})
                log.info("Anciens messages resumes automatiquement")
            except Exception as e:
                log.warning(f"Erreur resume: {e}")

    def repondre(self, user_message):
        self.historique.append({"role": "user", "content": user_message})
        if len(self.historique) > self.config["memoire"]["court_terme_max_messages"] * 1.5:
            self._resumer_anciens()
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
            erreur = self.derniere_erreur_groq or self.derniere_erreur_gemini or "cause inconnue"
            if detecter_langue(user_message) == "fr":
                texte = f"❌ LLM indisponible. Erreur: {erreur}. Vérifie les clés API dans Render → Environment."
            else:
                texte = f"❌ LLM unavailable. Error: {erreur}. Check Render → Environment variables."
        self.historique.append({"role": "assistant", "content": texte})
        return texte, self.llm_actif

    def _appeler_groq(self, messages, tentative=1):
        try:
            temps_attente = max(0, 2.0 - (time.time() - getattr(self, '_dernier_appel_groq', 0)))
            if temps_attente > 0:
                time.sleep(temps_attente)
            completion = self.groq_client.chat.completions.create(
                model=self.config["llm"]["modele_groq"],
                messages=messages,
                max_tokens=self.config["llm"]["max_tokens"],
                temperature=self.config["llm"]["temperature"]
            )
            self._dernier_appel_groq = time.time()
            return completion.choices[0].message.content
        except RateLimitError:
            self._dernier_appel_groq = time.time()
            if tentative < 4:
                duree = 2 ** tentative
                log.warning(f"Rate limit Groq, attente {duree}s (tentative {tentative}/3)")
                time.sleep(duree)
                return self._appeler_groq(messages, tentative + 1)
            err = "RateLimitError: limite atteinte apres 3 tentatives"
            log.warning(f"Erreur Groq: {err}")
            self.derniere_erreur_groq = err
            return None
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:150]}"
            log.warning(f"Erreur Groq: {err}")
            self.derniere_erreur_groq = err
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
            err = f"{type(e).__name__}: {str(e)[:150]}"
            log.warning(f"Erreur Gemini: {err}")
            self.derniere_erreur_gemini = err
            return None
