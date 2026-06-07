import logging
log = logging.getLogger("SKILLS_EXTERNAL")

class SkillsExternalLoader:
    def __init__(self, config):
        self.config = config

    def charger(self):
        log.info("Chargement skills externes (aucun pour l'instant)")
        return {}
