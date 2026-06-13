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
        from tools.built_in.calendrier import CalendrierOutil
        from tools.built_in.email import EmailOutil
        from tools.built_in.correction import CorrectionOutil
        from tools.built_in.notes import NotesOutil
        from tools.built_in.fiches import FichesOutil
        from tools.built_in.stats import StatsOutil
        from tools.built_in.site_web import SiteWebOutil
        from skills.built_in.recherche_web import RechercheWebSkill
        from skills.built_in.auto_install import AutoInstallSkill
        from skills.built_in.memoire import MemoireSkill
        from skills.built_in.meteo import MeteoSkill
        from skills.built_in.traducteur import TraducteurSkill
        from skills.built_in.rappel import RappelSkill
        from skills.built_in.conversation import ConversationSkill
        from tools.mcp.loader import MCPLoader

        mapping = {
            "calendrier": CalendrierOutil,
            "email": EmailOutil,
            "correction": CorrectionOutil,
            "notes": NotesOutil,
            "fiches": FichesOutil,
            "stats": StatsOutil,
            "site_web": SiteWebOutil,
            "recherche_web": RechercheWebSkill,
            "auto_install": AutoInstallSkill,
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
        mcp_loader = MCPLoader(self.config)
        outils_mcp = mcp_loader.charger()
        self.outils.update(outils_mcp)

    async def traiter_message(self, texte, user_id="default"):
        import re
        from core.router import detecter_intention, executer_intention
        if not self.llm.historique:
            self._restaurer_contexte(user_id)
        self.memory.ajouter_message("user", texte, user_id)
        intention = detecter_intention(texte)
        log.info(f"Intention detectee: {intention}")
        outil = executer_intention(intention, texte, self.outils)
        if outil:
            est_question = bool(re.search(r'\b(si|est-ce que|peux.tu|es.tu|vas.tu|qu-est-ce|comment)\b', texte.lower())) and '?' in texte
            if not est_question:
                try:
                    if hasattr(outil, 'executer'):
                        resultat = await outil.executer(texte)
                    else:
                        resultat = await outil(texte)
                    if resultat is not None:
                        return resultat, intention
                except Exception as e:
                    log.warning(f"Erreur outil {intention}: {e}")
        reponse, llm_utilise = self.llm.repondre(texte, user_id)
        self.memory.ajouter_message("assistant", reponse, user_id)
        return reponse, llm_utilise

    def _restaurer_contexte(self, user_id):
        profil = self.memory.charger_profil(user_id)
        identite = profil.get("identite")
        if identite:
            self.llm.historique.append({"role": "system", "content": f"[Profil utilisateur] {identite}"})
        resume = self.memory.charger_resume(user_id)
        if resume:
            self.llm.historique.append({"role": "system", "content": f"[Resume conversation precedente] {resume}"})
        messages = self.memory.charger_conversations_recentes(user_id)
        for m in messages:
            self.llm.historique.append({"role": m["role"], "content": m["content"]})
        if messages or resume or identite:
            log.info(f"Contexte restaure: {len(messages)} msgs + resume {'+ identite ' if identite else ' '}pour {user_id}")
        seuil = self.config["memoire"]["court_terme_max_messages"]
        if len(self.llm.historique) > seuil * 2:
            log.info("Proactive summarization before first user message")
            self.llm._resumer_anciens(user_id)
        # Extraire l'identite si absente du profil
        if not identite and messages:
            self.llm._extraire_identite(user_id)
