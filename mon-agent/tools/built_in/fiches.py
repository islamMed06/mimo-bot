import logging
log = logging.getLogger("FICHES")

class FichesOutil:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory

    async def executer(self, texte):
        if "fiche" in texte.lower() or "lecon" in texte.lower() or "lesson" in texte.lower():
            return "Donne-moi le sujet, le niveau (A1, A2, B1...) et la duree de la lecon."
        if "exercice" in texte.lower() or "exercise" in texte.lower():
            return "Donne-moi le sujet, le niveau et le nombre d'exercices souhaites."
        if "examen" in texte.lower() or "exam" in texte.lower() or "sujet" in texte.lower():
            return "Donne-moi le sujet, le niveau et la duree de l'examen."
        return "Fiches: dis-moi ce que tu veux generer (fiche de lecon, exercices, sujet d'examen)."
