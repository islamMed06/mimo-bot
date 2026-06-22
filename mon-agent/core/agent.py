import os
import json
import logging
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
log = logging.getLogger("AGENT")

class Agent:
    def __init__(self):
        self.config = self._charger_config()
        self.memory = None
        self.llm = None
        self.outils = {}
        self._initialiser()

    def _charger_config(self):
        chemin = os.path.join(os.path.dirname(__file__), "..", "config", "config.json")
        with open(chemin, "r", encoding="utf-8") as f:
            return json.load(f)

    def _initialiser(self):
        from core.memory import MemoryManager
        from core.llm import LLMManager
        self.memory = MemoryManager(self.config)
        self.llm = LLMManager(self.config, memory=self.memory)
        self._charger_outils()
        log.info(f"{self.config['agent']['nom']} v{self.config['agent']['version']} initialise")

    def _charger_outils(self):
        cfg_outils = self.config["tools"]["built_in"]
        from tools.built_in.site_web import SiteWebOutil
        from skills.built_in.recherche_web import RechercheWebSkill
        from skills.built_in.memoire import MemoireSkill
        from skills.built_in.meteo import MeteoSkill
        from skills.built_in.traducteur import TraducteurSkill
        from skills.built_in.rappel import RappelSkill
        from skills.built_in.conversation import ConversationSkill

        mapping = {
            "site_web": SiteWebOutil,
            "recherche_web": RechercheWebSkill,
            "memoire": MemoireSkill,
            "meteo": MeteoSkill,
            "traducteur": TraducteurSkill,
            "rappel": RappelSkill,
            "conversation": ConversationSkill,
        }
        for nom, classe in mapping.items():
            if nom in cfg_outils and cfg_outils[nom]:
                try:
                    self.outils[nom] = classe(self.config, self.memory)
                    log.info(f"Outil charge: {nom}")
                except Exception as e:
                    log.warning(f"Erreur chargement {nom}: {e}")

    def _build_tool_schemas(self):
        schemas = []
        for nom, outil in self.outils.items():
            if hasattr(outil, 'get_function_schema'):
                try:
                    schemas.append(outil.get_function_schema())
                except Exception as e:
                    log.warning(f"Schema {nom} ignoré: {e}")
        return schemas if schemas else None

    async def _router_result(self, texte, user_id, chat_id=None):
        from core.router import detecter_intention, executer_intention
        import re
        intention = detecter_intention(texte)
        if intention and intention != "conversation":
            outil = executer_intention(intention, texte, self.outils)
            if outil and hasattr(outil, 'executer'):
                est_question = bool(re.search(r'\b(si|est-ce que|peux.tu|es.tu|vas.tu|qu-est-ce|comment)\b', texte.lower())) and '?' in texte
                if not est_question:
                    for kwargs in [{"user_id": user_id, "chat_id": chat_id}, {"user_id": user_id}, {}]:
                        try:
                            resultat = await outil.executer(texte, **{k: v for k, v in kwargs.items() if v is not None})
                            if resultat:
                                log.info(f"Router a execute: {intention}")
                                return str(resultat)
                        except TypeError:
                            continue
                        except Exception as e:
                            log.warning(f"Erreur outil {intention}: {e}")
                            break
        return None

    async def traiter_message(self, texte, user_id="default", msg_date=None, chat_id=None):
        import re
        import asyncio
        import unicodedata
        from core.router import detecter_intention, executer_intention
        if not self.llm.historique:
            await self._restaurer_contexte(user_id)
        else:
            profil = await asyncio.to_thread(self.memory.charger_profil, user_id)
            identite = profil.get("identite")
            if identite and self.llm.identite_est_valide(identite) and not any(m["role"] == "system" and "[Profil utilisateur]" in m["content"] for m in self.llm.historique):
                self.llm.historique.insert(0, {"role": "system", "content": f"[Profil utilisateur] {identite}"})
                log.info(f"Profil utilisateur injecte dans historique existant")
        self.memory.ajouter_message("user", texte, user_id)
        # Detection auto si l'utilisateur se presente
        m_name = re.search(r"(?:je suis|je m'appelle|mon nom est|appelle.moi|moi c'est)\s+(.+)", texte.lower())
        if m_name:
            nom = m_name.group(1).strip().rstrip(".,!?;").title()
            if nom and len(nom) >= 2:
                profil = await asyncio.to_thread(self.memory.charger_profil, user_id)
                profil["identite"] = f"L'utilisateur s'appelle {nom}."
                await asyncio.to_thread(self.memory.sauvegarder_profil, profil, user_id)
                log.info(f"Identite definie via phrase: {nom}")
        # Phase 1: Function calling (max 2 iterations)
        schemas = self._build_tool_schemas()
        reponse, llm_utilise, tool_calls = self.llm.repondre(texte, user_id, msg_date=msg_date, tools=schemas)
        iterations = 0
        while tool_calls and iterations < 2:
            iterations += 1
            log.info(f"Tool calls (iter {iterations}): {[tc['function']['name'] for tc in tool_calls]}")
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                # Normaliser: stripper les accents (ex: meteo vs meteo)
                func_name_clean = unicodedata.normalize('NFKD', func_name).encode('ascii', 'ignore').decode('ascii')
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}
                outil = self.outils.get(func_name) or self.outils.get(func_name_clean)
                if outil and hasattr(outil, 'executer_args'):
                    try:
                        resultat = await outil.executer_args(**args, user_id=user_id, chat_id=chat_id)
                    except Exception as e:
                        resultat = f"Erreur outil {func_name}: {e}"
                elif outil and hasattr(outil, 'executer'):
                    try:
                        resultat = await outil.executer(texte, user_id=user_id)
                    except TypeError:
                        try:
                            resultat = await outil.executer(texte)
                        except Exception as e:
                            resultat = f"Erreur outil {func_name}: {e}"
                    except Exception as e:
                        resultat = f"Erreur outil {func_name}: {e}"
                else:
                    resultat = f"Outil {func_name} non disponible."
                self.llm.historique.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": str(resultat)
                })
            if iterations < 2:
                reponse, llm_utilise, tool_calls = self.llm.repondre(texte, user_id, tools=schemas)
            else:
                tool_calls = None
        if iterations > 0:
            reponse, llm_utilise = self.llm.reformuler_avec_outil(user_id)
            # Phase 1.5: si le LLM a appele le mauvais outil, le router peut corriger
            router_result = await self._router_result(texte, user_id, chat_id=chat_id)
            if router_result:
                reponse = router_result
            self.memory.ajouter_message("assistant", reponse, user_id)
            return reponse, llm_utilise
        # Phase 2: Fallback keyword router (si fonction calling non declenche)
        router_result = await self._router_result(texte, user_id, chat_id=chat_id)
        if router_result:
            reponse = router_result
        self.memory.ajouter_message("assistant", reponse, user_id)
        return reponse, llm_utilise

    async def _restaurer_contexte(self, user_id):
        import re
        import asyncio
        profil = await asyncio.to_thread(self.memory.charger_profil, user_id)
        identite = profil.get("identite")
        if identite and self.llm.identite_est_valide(identite):
            self.llm.historique.append({"role": "system", "content": f"[Profil utilisateur] {identite}"})
        super_data = await asyncio.to_thread(self.memory.charger_super_resume, user_id)
        if super_data:
            super_texte, super_date = super_data
            label = f"[Super-resume (mis a jour {super_date})]" if super_date else "[Super-resume]"
            self.llm.historique.append({"role": "system", "content": f"{label} {super_texte}"})
        recents = await asyncio.to_thread(self.memory.charger_resumes_recents, user_id, 3)
        for r in recents:
            self.llm.historique.append({"role": "system", "content": f"[Resume {r['date']}] {r['resume']}"})
        messages = await asyncio.to_thread(self.memory.charger_session_du_jour, user_id)
        for m in messages:
            self.llm.historique.append({"role": m["role"], "content": m["content"]})
        if (not identite or not self.llm.identite_est_valide(identite)) and messages:
            trouve = False
            for m in messages:
                m_name = re.search(r"(?:je suis|je m'appelle|mon nom est|appelle.moi|moi c'est)\s+(.+)", m["content"].lower())
                if m_name:
                    nom = m_name.group(1).strip().rstrip(".,!?;").title()
                    profil = await asyncio.to_thread(self.memory.charger_profil, user_id)
                    profil["identite"] = f"L'utilisateur s'appelle {nom}."
                    await asyncio.to_thread(self.memory.sauvegarder_profil, profil, user_id)
                    self.llm.historique.insert(0, {"role": "system", "content": f"[Profil utilisateur] L'utilisateur s'appelle {nom}."})
                    log.info(f"Identite restauree depuis historique: {nom}")
                    trouve = True
                    break
            if not trouve:
                resume_ctx = super_data[0] if super_data else None
                extraites = await asyncio.to_thread(self.llm._extraire_identite, user_id, messages, resume_ctx)
                if extraites:
                    self.llm.historique.insert(0, {"role": "system", "content": f"[Profil utilisateur] {extraites}"})
        if messages or super_data or identite or recents:
            log.info(f"Contexte restaure: {len(messages)} msgs + resume {'+ identite ' if identite else ' '}pour {user_id}")
