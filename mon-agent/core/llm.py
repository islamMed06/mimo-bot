import os
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from groq import Groq, RateLimitError
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
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.gemini_disponible = bool(self.gemini_key)
        self.llm_actif = "groq"
        self.historique = []
        for nom in ["groq", "gemini", "openrouter", "huggingface", "cloudflare", "github"]:
            setattr(self, f"derniere_erreur_{nom}", "")

    def get_system_prompt(self, user_message=None):
        maintenant = maintenant_algerie()
        jours_fr = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        mois_fr = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        jours_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        mois_en = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        jour_idx = maintenant.weekday()
        mois_idx = maintenant.month - 1
        aujourdhui_fr = f"{jours_fr[jour_idx]} {maintenant.day} {mois_fr[mois_idx]} {maintenant.year}"
        aujourdhui_en = f"{jours_en[jour_idx]} {maintenant.day} {mois_en[mois_idx]} {maintenant.year}"
        heure = maintenant.strftime("%H:%M")
        langue = "fr"
        if user_message:
            langue = detecter_langue(user_message)
        base_fr = (
            f"Tu es {self.config['agent']['nom']}, un assistant AI personnel modulaire et autonome. "
            f"Tu réponds toujours dans la langue de l'utilisateur. Sois concis, clair et utile. "
            f"Tu utilises Groq, Gemini, OpenRouter, HuggingFace, Cloudflare ou GitHub Models comme LLM (fallback automatique). "
            f"Tu disposes d'outils pour la gestion du calendrier, des emails, des notes élèves, des fiches de leçons, "
            f"des statistiques, de la correction d'exercices et du contrôle du site web. "
            f"Tu confirmes toujours avant les actions sensibles (création, modification, envoi, installation). "
            f"Tu n'effectues jamais seul des actions de suppression en masse ou de partage de données privées."
        )
        base_en = (
            f"You are {self.config['agent']['nom']}, a modular and autonomous personal AI assistant. "
            f"Always reply in the user's language. Be concise, clear, and helpful. "
            f"You use Groq, Gemini, OpenRouter, HuggingFace, Cloudflare or GitHub Models as LLM (auto fallback). "
            f"You have tools for calendar management, emails, student grades, lesson plans, "
            f"statistics, exercise correction, and website control. "
            f"You always confirm before sensitive actions (create, modify, send, install). "
            f"You never perform mass deletions or private data sharing on your own."
        )
        return base_en if langue == "en" else base_fr

    def _resumer_anciens(self, user_id=None):
        anciens = self.historique[:-self.config["memoire"]["court_terme_max_messages"]]
        if len(anciens) > 5:
            texte = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in anciens])
            try:
                completion = self.groq_client.chat.completions.create(
                    model=self.config["llm"]["modele_groq"],
                    messages=[{"role": "system", "content": "Resume cette conversation en 2-3 phrases en francais. PRESERVE les infos sur l'utilisateur (nom, profession, preferences, role)."},
                              {"role": "user", "content": texte}],
                    max_tokens=300
                )
                resume = completion.choices[0].message.content
                if self.memory:
                    self.memory.sauvegarder_resume(resume)
                self.historique = self.historique[-self.config["memoire"]["court_terme_max_messages"]:]
                self.historique.insert(0, {"role": "system", "content": f"[Resume conversation precedente] {resume}"})
                log.info(f"Anciens messages resumes automatiquement ({len(anciens)} msgs -> resume)")
            except Exception as e:
                log.warning(f"Erreur resume: {e}")
            # Extraire et sauvegarder l'identite utilisateur separement
            if self.memory and user_id:
                try:
                    comp = self.groq_client.chat.completions.create(
                        model=self.config["llm"]["modele_groq"],
                        messages=[{"role": "system", "content": "Extrais les infos personnelles de l'utilisateur (nom, profession, role, preferences). Reponds en 1 phrase max. Si aucune info, reponds 'RIEN'."},
                                  {"role": "user", "content": texte[:2000]}],
                        max_tokens=100
                    )
                    identite = comp.choices[0].message.content.strip()
                    if self.identite_est_valide(identite):
                        profil = self.memory.charger_profil(user_id)
                        profil["identite"] = identite
                        self.memory.sauvegarder_profil(profil, user_id)
                        log.info(f"Identite sauvegardee: {identite[:60]}")
                    else:
                        log.info(f"Identite ignoree ({identite[:40]})")
                except Exception as e:
                    log.warning(f"Erreur extraction identite: {e}")

    def identite_est_valide(self, identite):
        if not identite:
            return False
        s = identite.strip().rstrip(".,!?;").lower()
        if s in ("rien", "aucune", "inconnu", "unknown", "none", "no info"):
            return False
        if s.startswith("la date") or s.startswith("the date") or s.startswith("aujourd"):
            return False
        if len(s) < 10:
            return False
        return True

    def _extraire_identite(self, user_id, messages=None):
        try:
            if not messages:
                messages = self.historique[-40:]
            texte = "\n".join([f"{m['role']}: {m['content'][:300]}" for m in messages])
            comp = self.groq_client.chat.completions.create(
                model=self.config["llm"]["modele_groq"],
                messages=[{"role": "system", "content": "Extrais les infos personnelles de l'utilisateur (nom, profession, role, preferences). Reponds en 1 phrase max. Si aucune info, reponds 'RIEN'."},
                          {"role": "user", "content": texte[:3000]}],
                max_tokens=100
            )
            identite = comp.choices[0].message.content.strip()
            if self.identite_est_valide(identite):
                profil = self.memory.charger_profil(user_id)
                profil["identite"] = identite
                self.memory.sauvegarder_profil(profil, user_id)
                log.info(f"Identite extraite: {identite[:60]}")
                return identite
            log.info(f"Identite extraite ignoree ({identite[:40]})")
        except Exception as e:
            log.warning(f"Erreur extraction identite: {e}")
        return None

    def repondre(self, user_message, user_id=None):
        self.historique.append({"role": "user", "content": user_message})
        if len(self.historique) > self.config["memoire"]["court_terme_max_messages"] * 2:
            self._resumer_anciens(user_id)
        system_prompt = self.get_system_prompt(user_message)
        maintenant = maintenant_algerie()
        contexte_date = f"Auj: {maintenant.day:02d}/{maintenant.month:02d}/{maintenant.year} {maintenant.strftime('%H:%M')} (Algerie UTC+1). REGLE ABSOLUE: ne mentionne jamais la date/heure sauf si l'utilisateur demande explicitement. Meme pour 'bonjour'/'bonsoir'."
        messages = [{"role": "system", "content": system_prompt}, {"role": "system", "content": contexte_date}]
        limite = self.config["memoire"]["court_terme_max_messages"]
        # Inclure TOUS les messages system (resumes) en preservant l'ordre
        for msg in self.historique:
            if msg["role"] == "system":
                messages.append(msg)
        # Puis les messages user/assistant les plus recents
        recents = [m for m in self.historique if m["role"] != "system"]
        for msg in recents[-limite:]:
            messages.append(msg)
        fallbacks = [
            ("groq", self._appeler_groq),
            ("gemini", self._appeler_gemini),
        ]
        if os.getenv("OPENROUTER_API_KEY"):
            fallbacks.append(("openrouter", self._appeler_openrouter))
        if os.getenv("HF_API_KEY"):
            fallbacks.append(("huggingface", self._appeler_huggingface))
        if os.getenv("CLOUDFLARE_API_TOKEN"):
            fallbacks.append(("cloudflare", self._appeler_cloudflare))
        if os.getenv("GITHUB_TOKEN"):
            fallbacks.append(("github", self._appeler_github))
        for nom, methode in fallbacks:
            texte = methode(messages)
            if texte:
                self.llm_actif = nom
                break
            log.info(f"{nom} indisponible, fallback suivant...")
        if texte is None:
            erreurs_llm = [getattr(self, f"derniere_erreur_{n}", "") for n in ["groq", "gemini", "openrouter", "huggingface", "cloudflare", "github"]]
            erreur = next((e for e in erreurs_llm if e), "cause inconnue")
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
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            system_msg = messages[0]["content"]
            user_msgs = [m["content"] for m in messages[1:]]
            prompt = f"{system_msg}\n\n" + "\n".join(user_msgs)
            model = genai.GenerativeModel(self.config["llm"]["modele_gemini"])
            reponse = model.generate_content(prompt)
            import gc; gc.collect()
            return reponse.text
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:150]}"
            log.warning(f"Erreur Gemini: {err}")
            self.derniere_erreur_gemini = err
            return None

    def _appeler_openai_compat(self, url, api_key, model, messages, nom):
        import httpx
        try:
            resp = httpx.post(url, json={
                "model": model, "messages": messages,
                "max_tokens": self.config["llm"]["max_tokens"],
                "temperature": self.config["llm"]["temperature"]
            }, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
            if resp.status_code == 429:
                err = f"RateLimitError: {resp.text[:100]}"
                setattr(self, f"derniere_erreur_{nom}", err)
                log.warning(f"Rate limit {nom}: {err}")
                return None
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:150]}"
            log.warning(f"Erreur {nom}: {err}")
            setattr(self, f"derniere_erreur_{nom}", err)
            return None

    def _appeler_openrouter(self, messages):
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            return None
        return self._appeler_openai_compat(
            "https://openrouter.ai/api/v1/chat/completions",
            key, self.config["llm"]["modele_openrouter"], messages, "openrouter"
        )

    def _appeler_huggingface(self, messages):
        key = os.getenv("HF_API_KEY")
        if not key:
            return None
        return self._appeler_openai_compat(
            "https://api-inference.huggingface.co/v1/chat/completions",
            key, self.config["llm"]["modele_huggingface"], messages, "huggingface"
        )

    def _appeler_cloudflare(self, messages):
        key = os.getenv("CLOUDFLARE_API_TOKEN")
        account = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        if not key or not account:
            return None
        return self._appeler_openai_compat(
            f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1/chat/completions",
            key, self.config["llm"]["modele_cloudflare"], messages, "cloudflare"
        )

    def _appeler_github(self, messages):
        key = os.getenv("GITHUB_TOKEN")
        if not key:
            return None
        return self._appeler_openai_compat(
            "https://models.inference.ai.azure.com/chat/completions",
            key, self.config["llm"]["modele_github"], messages, "github"
        )
