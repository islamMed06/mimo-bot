import os
import json
import logging
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore

log = logging.getLogger("MEMORY")

class MemoryManager:
    def __init__(self, config):
        self.config = config
        self.court_terme = []
        self.court_terme_max = config["memoire"]["court_terme_max_messages"]
        self.db = None
        self._init_firebase()

    def _init_firebase(self):
        try:
            if not firebase_admin._apps:
                pk = os.getenv("FIREBASE_PRIVATE_KEY", "")
                if pk:
                    pk = pk.replace("\\n", "\n")
                    pk = pk.strip('"')
                cred_dict = {
                    "type": "service_account",
                    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                    "private_key": pk,
                    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
                if not cred_dict["private_key"]:
                    log.warning("Firebase non configure, memoire long terme desactivee")
                    return
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {
                    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET")
                })
            self.db = firestore.client()
            log.info("Firebase initialise")
        except Exception as e:
            log.warning(f"Erreur initialisation Firebase: {e}")

    def ajouter_message(self, role, contenu, user_id="default"):
        maintenant = datetime.now()
        self.court_terme.append({
            "role": role,
            "contenu": contenu,
            "timestamp": maintenant.isoformat()
        })
        if len(self.court_terme) > self.court_terme_max:
            self._compresser_court_terme()
        if self.db:
            self._sauvegarder_firebase(role, contenu, user_id)

    def _compresser_court_terme(self):
        if len(self.court_terme) < 3:
            return
        resume = self._generer_resume(self.court_terme[:-5])
        self.court_terme = self.court_terme[-5:]
        self.court_terme.insert(0, {"role": "resume", "contenu": resume, "timestamp": datetime.now().isoformat()})

    def _generer_resume(self, messages):
        sujets = []
        for m in messages:
            c = m.get("contenu", "")[:100]
            sujets.append(c)
        return f"Resume session: {' | '.join(sujets[-5:])}"

    def sauvegarder_resume(self, resume, user_id="default"):
        if not self.db:
            return
        try:
            ref = self.db.collection("conversations").document(user_id).collection("resumes").document("dernier")
            ref.set({"resume": resume, "timestamp": datetime.now().isoformat()})
        except Exception as e:
            log.warning(f"Erreur sauvegarde resume: {e}")

    def charger_resume(self, user_id="default"):
        if not self.db:
            return None
        try:
            doc = self.db.collection("conversations").document(user_id).collection("resumes").document("dernier").get()
            if doc.exists:
                return doc.to_dict().get("resume")
        except Exception as e:
            log.warning(f"Erreur chargement resume: {e}")
        return None

    def _sauvegarder_firebase(self, role, contenu, user_id):
        try:
            maintenant = datetime.now()
            session_id = maintenant.strftime("%Y-%m-%d")
            doc_ref = self.db.collection("conversations").document(user_id).collection("sessions").document(session_id)
            doc_ref.set({
                "messages": firestore.ArrayUnion([{
                    "role": role,
                    "contenu": contenu[:500],
                    "timestamp": maintenant.isoformat()
                }]),
                "derniere_activite": maintenant.isoformat()
            }, merge=True)
        except Exception as e:
            log.warning(f"Erreur sauvegarde Firebase: {e}")

    def charger_conversations_recentes(self, user_id="default", limit=150):
        if not self.db:
            return []
        try:
            sessions = list(self.db.collection("conversations").document(user_id).collection("sessions") \
                .order_by("derniere_activite", direction=firestore.Query.DESCENDING).limit(3).get())
            messages = []
            for session in sessions:
                data = session.to_dict()
                if "messages" in data:
                    for msg in data["messages"]:
                        ts = msg.get("timestamp", "")
                        date_prefix = ""
                        if ts:
                            try:
                                d = ts[:10]
                                from datetime import date
                                aujourdhui = date.today().isoformat()
                                if d != aujourdhui:
                                    date_prefix = f"[{d}] "
                            except:
                                pass
                        messages.append({
                            "role": msg.get("role", "assistant"),
                            "content": date_prefix + msg.get("contenu", "")
                        })
            log.info(f"Charge historique: {len(messages)} messages depuis {len(sessions)} sessions")
            return messages[-limit:]
        except Exception as e:
            log.warning(f"Erreur chargement historique: {e}")
            return []

    def get_contexte(self, user_id="default"):
        contexte = []
        for m in self.court_terme:
            contexte.append(f"{m['role']}: {m['contenu']}")
        return "\n".join(contexte)

    def charger_profil(self, user_id="default"):
        if not self.db:
            return self._profil_par_defaut()
        try:
            doc = self.db.collection("user_profile").document(user_id).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            log.warning(f"Erreur chargement profil: {e}")
        return self._profil_par_defaut()

    def _profil_par_defaut(self):
        return {
            "preferences": {"langue": "fr", "style_reponse": "court"},
            "routine": {},
            "habitudes": []
        }

    def sauvegarder_profil(self, profil, user_id="default"):
        if not self.db:
            return
        try:
            self.db.collection("user_profile").document(user_id).set(profil, merge=True)
        except Exception as e:
            log.warning(f"Erreur sauvegarde profil: {e}")
