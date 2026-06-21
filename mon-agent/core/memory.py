import os
import json
import logging
from uuid import uuid4
from datetime import datetime, timezone, timedelta
import firebase_admin
from firebase_admin import credentials, firestore

ALGERIA_TZ = timezone(timedelta(hours=1))
log = logging.getLogger("MEMORY")

class ProfileCache:
    def __init__(self, ttl=60):
        self._cache = {}
        self._ttl = ttl

    def get(self, user_id, loader):
        entry = self._cache.get(user_id)
        if entry and datetime.now().timestamp() - entry["ts"] < self._ttl:
            return entry["profil"]
        profil = loader(user_id)
        self._cache[user_id] = {"profil": profil, "ts": datetime.now().timestamp()}
        return profil

    def invalidate(self, user_id):
        self._cache.pop(user_id, None)

class MemoryManager:
    def __init__(self, config):
        self.config = config
        self.court_terme = {}
        self.court_terme_max = config["memoire"]["court_terme_max_messages"]
        self.db = None
        self._cache_profil = ProfileCache(ttl=60)
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
        self.court_terme.setdefault(user_id, []).append({
            "role": role,
            "contenu": contenu,
            "timestamp": maintenant.isoformat()
        })
        if len(self.court_terme[user_id]) > self.court_terme_max:
            self._compresser_court_terme(user_id)
        if self.db:
            self._sauvegarder_firebase(role, contenu, user_id)

    def _compresser_court_terme(self, user_id):
        msgs = self.court_terme.get(user_id, [])
        if len(msgs) < 3:
            return
        resume = self._generer_resume(msgs[:-self.court_terme_max])
        self.court_terme[user_id] = msgs[-self.court_terme_max:]
        self.court_terme[user_id].insert(0, {"role": "resume", "contenu": resume, "timestamp": datetime.now(ALGERIA_TZ).isoformat()})

    def _generer_resume(self, messages):
        sujets = []
        for m in messages:
            c = m.get("contenu", "")[:100]
            sujets.append(c)
        return f"Resume session: {' | '.join(sujets[-5:])}"

    def sauvegarder_resume(self, resume, user_id="default", date_str=None):
        if not self.db:
            return
        try:
            maintenant = datetime.now(ALGERIA_TZ)
            ref = self.db.collection("conversations").document(user_id).collection("resumes").document("dernier")
            ref.set({"resume": resume, "timestamp": maintenant.isoformat()})
            if date_str:
                ref_date = self.db.collection("conversations").document(user_id).collection("resumes").document(date_str)
                ref_date.set({"resume": resume, "timestamp": maintenant.isoformat()})
        except Exception as e:
            log.warning(f"Erreur sauvegarde resume: {e}")

    def sauvegarder_super_resume(self, resume, user_id="default"):
        if not self.db:
            return
        try:
            maintenant = datetime.now(ALGERIA_TZ)
            ref = self.db.collection("conversations").document(user_id).collection("resumes").document("super")
            ref.set({"resume": resume, "timestamp": maintenant.isoformat(), "derniere_mise_a_jour": maintenant.isoformat()})
            log.info(f"Super-resume mis a jour pour {user_id}")
        except Exception as e:
            log.warning(f"Erreur sauvegarde super-resume: {e}")

    def charger_super_resume(self, user_id="default"):
        if not self.db:
            return None
        try:
            doc = self.db.collection("conversations").document(user_id).collection("resumes").document("super").get()
            if doc.exists:
                data = doc.to_dict()
                return data.get("resume"), data.get("timestamp", "")[:10]
        except Exception as e:
            log.warning(f"Erreur chargement super-resume: {e}")
        return None

    def charger_resumes_recents(self, user_id="default", jours=7):
        if not self.db:
            return []
        try:
            aujourdhui = datetime.now(ALGERIA_TZ)
            resumes = []
            for i in range(1, jours + 1):
                date_str = (aujourdhui - timedelta(days=i)).strftime("%Y-%m-%d")
                doc = self.db.collection("conversations").document(user_id).collection("resumes").document(date_str).get()
                if doc.exists:
                    data = doc.to_dict()
                    resume = data.get("resume", "")
                    ts = data.get("timestamp", "")[:10]
                    if resume:
                        resumes.append({"date": ts, "resume": resume})
            return resumes
        except Exception as e:
            log.warning(f"Erreur chargement resumes recents: {e}")
            return []

    def charger_resume(self, user_id="default"):
        if not self.db:
            return None
        try:
            doc = self.db.collection("conversations").document(user_id).collection("resumes").document("dernier").get()
            if doc.exists:
                data = doc.to_dict()
                resume = data.get("resume")
                ts = data.get("timestamp", "")
                return resume, ts[:10] if ts else None
        except Exception as e:
            log.warning(f"Erreur chargement resume: {e}")
        return None

    def charger_session_du_jour(self, user_id="default"):
        if not self.db:
            return []
        aujourdhui = datetime.now(ALGERIA_TZ).strftime("%Y-%m-%d")
        try:
            doc = self.db.collection("conversations").document(user_id).collection("sessions").document(aujourdhui).get()
            if doc.exists:
                data = doc.to_dict()
                msgs = data.get("messages", []) if data else []
                if msgs is None:
                    sub = list(self.db.collection("conversations").document(user_id)
                        .collection("sessions").document(aujourdhui)
                        .collection("messages").order_by("timestamp").get())
                    msgs = [s.to_dict() for s in sub]
                return [{"role": m.get("role", "assistant"), "content": m.get("contenu", "")} for m in msgs]
            return []
        except Exception as e:
            log.warning(f"Erreur chargement session du jour: {e}")
            return []

    def _sauvegarder_firebase(self, role, contenu, user_id):
        try:
            import traceback
            maintenant = datetime.now(ALGERIA_TZ)
            session_id = maintenant.strftime("%Y-%m-%d")
            doc_ref = self.db.collection("conversations").document(user_id).collection("sessions").document(session_id)
            if len(contenu) > 500:
                log.warning(f"Message tronque: {len(contenu)} chars → 500 (user={user_id})")
            msg = {"role": role, "contenu": contenu[:500], "timestamp": maintenant.isoformat()}
            self._sauvegarder_firebase_atomique(doc_ref, msg, user_id, session_id, maintenant)
            log.info(f"Firebase: {role} message sauvegarde ({session_id})")
        except Exception as e:
            log.warning(f"Erreur sauvegarde Firebase: {traceback.format_exc()}")

    def _sauvegarder_firebase_atomique(self, doc_ref, msg, user_id, session_id, maintenant, retry=3):
        for t in range(retry):
            try:
                transaction = self.db.transaction()
                doc = doc_ref.get(transaction=transaction)
                if doc.exists:
                    data = doc.to_dict()
                    msgs = data.get("messages", [])
                    if not msgs:
                        sub = list(self.db.collection("conversations").document(user_id)
                            .collection("sessions").document(session_id)
                            .collection("messages")
                            .order_by("timestamp").get())
                        if sub:
                            msgs = [s.to_dict() for s in sub]
                    msgs.append(msg)
                    transaction.set(doc_ref, {"messages": msgs, "derniere_activite": maintenant.isoformat()})
                else:
                    transaction.set(doc_ref, {"messages": [msg], "derniere_activite": maintenant.isoformat()})
                transaction.commit()
                return
            except Exception as e:
                if t == retry - 1:
                    raise
                log.warning(f"Retry {t+1}/{retry} sauvegarde Firebase: {e}")

    def charger_conversations_recentes(self, user_id="default", limit=40):
        if not self.db:
            return []
        try:
            session_limit = max(1, min(10, limit // 20))
            sessions = list(self.db.collection("conversations").document(user_id).collection("sessions") \
                .order_by("derniere_activite", direction=firestore.Query.DESCENDING).limit(session_limit).get())
            messages = []
            for session in sessions:
                data = session.to_dict()
                sid = session.id
                msgs_data = data.get("messages") if data else None
                if msgs_data is None:
                    # backward compat: session doc may have no "messages" field
                    # (created by earlier subcollection format), check subcollection
                    sub = list(self.db.collection("conversations").document(user_id)
                        .collection("sessions").document(sid)
                        .collection("messages")
                        .order_by("timestamp").get())
                    msgs_data = [s.to_dict() for s in sub]
                for msg in msgs_data:
                    ts = msg.get("timestamp", "")
                    date_prefix = ""
                    if ts:
                        try:
                            d = ts[:10]
                            aujourdhui = datetime.now(ALGERIA_TZ).date().isoformat()
                            if d != aujourdhui:
                                date_prefix = f"[{d}] "
                        except (ValueError, TypeError):
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
        for m in self.court_terme.get(user_id, []):
            contexte.append(f"{m['role']}: {m['contenu']}")
        return "\n".join(contexte)

    def compter_sessions(self, user_id="default"):
        if not self.db:
            return 0
        try:
            sessions = list(self.db.collection("conversations").document(user_id).collection("sessions").select([]).get())
            return len(sessions)
        except Exception as e:
            log.warning(f"Erreur comptage sessions: {e}")
            return -1

    @staticmethod
    def resoudre_user_id(user_id_telegram):
        admin_tg = os.getenv("ADMIN_TELEGRAM_ID")
        admin_supabase = os.getenv("ADMIN_SUPABASE_ID")
        if admin_tg and admin_supabase and user_id_telegram == admin_tg:
            log.info("Admin Telegram → Supabase ID mapping")
            return admin_supabase
        return user_id_telegram

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
        return self._cache_profil.get(user_id, self._charger_profil_firestore)

    def _charger_profil_firestore(self, user_id):
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
            self._cache_profil.invalidate(user_id)
        except Exception as e:
            log.warning(f"Erreur sauvegarde profil: {e}")

    # ── Rappels ──────────────────────────────────────
    def ajouter_rappel(self, user_id, message, timestamp_iso):
        if not self.db:
            return None
        try:
            doc_id = uuid4().hex
            data = {"user_id": user_id, "message": message, "timestamp": timestamp_iso,
                    "cree_le": datetime.now(ALGERIA_TZ).isoformat(), "envoye": False}
            self.db.collection("reminders").document(doc_id).set(data)
            return doc_id
        except Exception as e:
            log.warning(f"Erreur ajout rappel: {e}")
            return None

    def liste_rappels(self, user_id, actifs=True):
        if not self.db:
            return {}
        try:
            from google.cloud.firestore_v1 import FieldFilter
            docs = self.db.collection("reminders").where(filter=FieldFilter("user_id", "==", user_id)).stream()
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
            doc = self.db.collection("reminders").document(doc_id).get()
            if not doc.exists:
                return False
            if doc.to_dict().get("user_id") != user_id:
                log.warning(f"Tentative suppression rappel {doc_id} par user {user_id} non proprietaire")
                return False
            self.db.collection("reminders").document(doc_id).delete()
            return True
        except Exception as e:
            log.warning(f"Erreur suppression rappel: {e}")
            return False

    def rappels_echus(self):
        if not self.db:
            return []
        try:
            maintenant = datetime.now(ALGERIA_TZ)
            maintenant_iso = maintenant.isoformat()
            echus = []
            docs = self.db.collection("reminders").stream()
            for doc in docs:
                data = doc.to_dict()
                if data.get("envoye") == False and data.get("timestamp", "") <= maintenant_iso:
                    echus.append({"user_id": data["user_id"], "doc_id": doc.id, "message": data.get("message", "")})
                    if len(echus) >= 100:
                        break
            log.info(f"rappels_echus: {len(echus)} echus")
            return echus
        except Exception as e:
            log.warning(f"Erreur verification rappels: {e}")
            return []

    def marquer_envoye(self, user_id, doc_id):
        if not self.db:
            return
        try:
            doc = self.db.collection("reminders").document(doc_id).get()
            if not doc.exists:
                return
            if doc.to_dict().get("user_id") != user_id:
                log.warning(f"Tentative marquage rappel {doc_id} par user {user_id} non proprietaire")
                return
            self.db.collection("reminders").document(doc_id).update({"envoye": True})
        except Exception as e:
            log.warning(f"Erreur marquage rappel: {e}")
