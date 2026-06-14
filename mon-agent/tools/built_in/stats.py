import logging
log = logging.getLogger("STATS")

class StatsOutil:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory
        self._plt = None

    def _get_plt(self):
        if self._plt is None:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import io as _io
            self._plt = plt
            self._io = _io
        return self._plt, self._io

    async def executer(self, texte):
        texte_lower = texte.lower()
        if "graphique" in texte_lower or "chart" in texte_lower or "graph" in texte_lower:
            return "Pour generer un graphique, donne-moi la classe a analyser."
        if "moyenne" in texte_lower or "average" in texte_lower:
            return "Donne-moi le nom de la classe pour voir les statistiques."
        if "rapport" in texte_lower or "report" in texte_lower:
            return "Donne-moi la classe pour generer un rapport."
        return "Stats: donne-moi une classe pour voir les statistiques ou generer un graphique."

    async def generer_graphique(self, donnees, titre="Notes de la classe"):
        try:
            plt, io = self._get_plt()
            fig, ax = plt.subplots(figsize=(8, 5))
            eleves = list(donnees.keys())
            notes = list(donnees.values())
            ax.bar(eleves, notes, color="#4CAF50")
            ax.set_title(titre)
            ax.set_ylabel("Notes")
            ax.set_ylim(0, 20)
            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            plt.close()
            return buf
        except Exception as e:
            log.warning(f"Erreur generation graphique: {e}")
            return None
