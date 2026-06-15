import os
import json
import logging
from datetime import datetime, timezone, timedelta
import firebase_admin
from firebase_admin import credentials, firestore

ALGERIA_TZ = timezone(timedelta(hours=1))
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
        maintenant = datetime.now(ALGERIA_TZ)
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
        self.court_terme.insert(0, {"role": "resume", "contenu": resume, "timestamp": datetime.now(ALGERIA_TZ).isoformat()})

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
            ref.set({"resume": resume, "timestamp": datetime.now(ALGERIA_TZ).isoformat()})
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
            maintenant = datetime.now(ALGERIA_TZ)
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

    def charger_conversations_recentes(self, user_id="default", limit=40):
        if not self.db:
            return []
        try:
            sessions = list(self.db.collection("conversations").document(user_id).collection("sessions") \
                .order_by("derniere_activite", direction=firestore.Query.DESCENDING).limit(2).get())
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
                                aujourdhui = datetime.now(ALGERIA_TZ).date().isoformat()
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

    def compter_sessions(self, user_id="default"):
        if not self.db:
            return 0
        try:
            sessions = list(self.db.collection("conversations").document(user_id).collection("sessions").get())
            return len(sessions)
        except Exception as e:
            log.warning(f"Erreur comptage sessions: {e}")
            return -1

    def test_lecture_ecriture(self, user_id="default"):
        if not self.db:
            return "Firebase DB non initialise"
        try:
            from datetime import datetime
            ref = self.db.collection("_tests").document(user_id)
            ref.set({"test": "ok", "ts": datetime.now(ALGERIA_TZ).isoformat()}, merge=True)
            doc = ref.get()
            if doc.exists:
                return f"Ecriture/Lecture OK -> {doc.to_dict().get('test')}"
            return "Document non trouve apres ecriture"
        except Exception as e:
            return f"Erreur test Firebase: {e}"

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

    # ── Rappels ──────────────────────────────────────
    def ajouter_rappel(self, user_id, message, timestamp_iso):
        if not self.db:
            return None
        try:
            from datetime import datetime
            doc_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
            ref = self.db.collection("reminders").document(user_id).collection("items").document(doc_id)
            ref.set({"message": message, "timestamp": timestamp_iso, "cree_le": datetime.now(ALGERIA_TZ).isoformat(), "envoye": False})
            return doc_id
        except Exception as e:
            log.warning(f"Erreur ajout rappel: {e}")
            return None

    def liste_rappels(self, user_id, actifs=True):
        if not self.db:
            return {}
        try:
            ref = self.db.collection("reminders").document(user_id).collection("items")
            docs = ref.where("envoye", "==", not actifs).stream() if not actifs else ref.stream()
            rappels = {}
            for d in docs:
                data = d.to_dict()
                if actifs and not data.get("envoye", False):
                    rappels[d.id] = data
                elif not actifs and data.get("envoye", False):
                    rappels[d.id] = data
            return rappels
        except Exception as e:
            log.warning(f"Erreur liste rappels: {e}")
            return {}

    def supprimer_rappel(self, user_id, doc_id):
        if not self.db:
            return False
        try:
            self.db.collection("reminders").document(user_id).collection("items").document(doc_id).delete()
            return True
        except Exception as e:
            log.warning(f"Erreur suppression rappel: {e}")
            return False

    def rappels_echus(self):
        """Retourne tous les rappels (tous users) dont l'echeance est passee et non envoyes"""
        if not self.db:
            return []
        try:
            maintenant = datetime.now(ALGERIA_TZ).isoformat()
            users = self.db.collection("reminders").stream()
            echus = []
            for user_doc in users:
                user_id = user_doc.id
                items = self.db.collection("reminders").document(user_id).collection("items").where("envoye", "==", False).stream()
                for item in items:
                    data = item.to_dict()
                    if data.get("timestamp", "") <= maintenant:
                        echus.append({"user_id": user_id, "doc_id": item.id, "message": data.get("message", "")})
            return echus
        except Exception as e:
            log.warning(f"Erreur verification rappels: {e}")
            return []

    def marquer_envoye(self, user_id, doc_id):
        if not self.db:
            return
        try:
            self.db.collection("reminders").document(user_id).collection("items").document(doc_id).update({"envoye": True})
        except Exception as e:
            log.warning(f"Erreur marquage rappel: {e}")
