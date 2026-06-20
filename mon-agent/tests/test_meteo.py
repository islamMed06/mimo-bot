import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skills.built_in.meteo import MeteoSkill

@pytest.fixture
def skill():
    return MeteoSkill({}, None)

class TestExtraireVille:
    def test_apres_a(self, skill):
        assert skill._extraire_ville("meteo a Paris") == "Paris"

    def test_apres_de(self, skill):
        assert skill._extraire_ville("meteo d Alger") == "Alger"

    def test_apres_weather_in(self, skill):
        assert skill._extraire_ville("weather in London") == "London"

    def test_apres_meteo(self, skill):
        assert skill._extraire_ville("meteo Oran") == "Oran"

    def test_dernier_mot_significatif(self, skill):
        assert skill._extraire_ville("donne la meteo") in ("Alger",)

    def test_stop_words_ignored(self, skill):
        ville = skill._extraire_ville("donne la temperature")
        assert ville == "Alger"
