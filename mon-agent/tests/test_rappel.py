import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skills.built_in.rappel import RappelSkill

@pytest.fixture
def skill():
    return RappelSkill({"memoire": {}}, None)

class TestExtraireMinutes:
    def test_minutes(self, skill):
        assert skill._extraire_minutes("dans 30 min de test") == 30

    def test_heures(self, skill):
        assert skill._extraire_minutes("dans 2 heures de test") == 120

    def test_heure_abreviation(self, skill):
        assert skill._extraire_minutes("dans 1h de test") == 60

    def test_secondes(self, skill):
        assert skill._extraire_minutes("dans 90 secondes") == 1

    def test_aucune_duree(self, skill):
        assert skill._extraire_minutes("test sans duree") is None

class TestExtraireMessage:
    def test_avec_separateur_de(self, skill):
        assert skill._extraire_message("dans 30 min de corriger les copies") == "corriger les copies"

    def test_avec_separateur_pour(self, skill):
        assert skill._extraire_message("dans 10 min pour acheter du pain") == "acheter du pain"

    def test_sans_message(self, skill):
        assert skill._extraire_message("dans 5 min") == ""

class TestFmtDuree:
    def test_minutes_seules(self, skill):
        assert skill._fmt_duree(30) == "30min"

    def test_heures_exactes(self, skill):
        assert skill._fmt_duree(120) == "2h"

    def test_heures_et_minutes(self, skill):
        assert skill._fmt_duree(90) == "1h30min"
