import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skills.built_in.traducteur import TraducteurSkill

@pytest.fixture
def skill():
    return TraducteurSkill({}, None)

class TestAnalyser:
    def test_cible_anglais(self, skill):
        cible, source, texte = skill._analyser("traduis bonjour en anglais")
        assert cible == "en"

    def test_cible_francais(self, skill):
        cible, source, texte = skill._analyser("translate hello to french")
        assert cible == "fr"

    def test_source_allemand(self, skill):
        cible, source, texte = skill._analyser("traduis guten tag du allemand en anglais")
        assert source == "de"

    def test_texte_entre_guillemets(self, skill):
        cible, source, texte = skill._analyser('traduis "hello world" en francais')
        assert texte == "hello world"

    def test_texte_sans_guillemets(self, skill):
        cible, source, texte = skill._analyser("traduis hello world en francais")
        assert texte == "hello world en francais"
