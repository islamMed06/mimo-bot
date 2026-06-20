import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.router import detecter_intention, executer_intention, MOTS_CLEFS

class TestDetecterIntention:
    def test_meteo_detectee(self):
        assert detecter_intention("Quelle est la meteo a Alger?") == "meteo"

    def test_rappel_detecte(self):
        assert detecter_intention("programme un rappel dans 30 min de test") == "rappel"

    def test_traduction_detectee(self):
        assert detecter_intention("traduis bonjour en anglais") == "traduction"

    def test_recherche_detectee(self):
        assert detecter_intention("cherche sur internet python") == "recherche"

    def test_conversation_par_defaut(self):
        assert detecter_intention("Comment ca va ?") == "conversation"

    def test_exclusion_rappel(self):
        assert detecter_intention("Tu te rappelles de moi ?") not in ("rappel",)

    def test_site_web_detecte(self):
        assert detecter_intention("liste des utilisateurs") == "site_web"


class TestExecuterIntention:
    def test_mapping_meteo(self):
        outils = {"meteo": "objet_meteo"}
        assert executer_intention("meteo", "", outils) == "objet_meteo"

    def test_mapping_inconnu(self):
        assert executer_intention("inconnu", "", {}) is None
