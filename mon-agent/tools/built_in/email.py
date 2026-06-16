import logging
log = logging.getLogger("EMAIL")

class EmailOutil:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory

    async def executer(self, texte):
        texte_lower = texte.lower()
        if "envoi" in texte_lower or "send" in texte_lower:
            return "Pour envoyer un email, donne-moi le destinataire, le sujet et le message. Je confirme avant d'envoyer."
        if "lit" in texte_lower or "read" in texte_lower or "voir" in texte_lower:
            return "Fonction lecture emails pas encore connectee a un compte IMAP."
        if "resume" in texte_lower or "resume" in texte_lower or "summary" in texte_lower:
            return "Fonction resume emails pas encore connectee."
        return "Email: dis-moi ce que tu veux faire (lire, envoyer, resumer)."
