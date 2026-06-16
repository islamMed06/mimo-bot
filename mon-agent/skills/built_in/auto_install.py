import os
import subprocess
import logging

log = logging.getLogger("AUTO_INSTALL")

class AutoInstallSkill:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory

    async def executer(self, texte):
        if "installe" in texte.lower() or "install" in texte.lower() or "ajoute" in texte.lower() or "add" in texte.lower():
            return "Quel outil veux-tu installer ? Donne-moi le nom ou le package Python."
        return "Auto-installation: dis-moi ce que tu veux installer."

    async def installer(self, package):
        try:
            resultat = subprocess.run(
                [os.sys.executable, "-m", "pip", "install", package],
                capture_output=True, text=True, timeout=60
            )
            if resultat.returncode == 0:
                return f"Package '{package}' installe avec succes."
            return f"Erreur installation '{package}': {resultat.stderr}"
        except Exception as e:
            return f"Erreur: {e}"
