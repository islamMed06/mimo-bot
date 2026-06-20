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

    @staticmethod
    def get_function_schema():
        return {
            "type": "function",
            "function": {
                "name": "email",
                "description": "Envoyer ou lire des emails",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["envoyer", "lire"],
                            "description": "Action à effectuer"
                        },
                        "destinataire": {
                            "type": "string",
                            "description": "Adresse email du destinataire"
                        },
                        "sujet": {
                            "type": "string",
                            "description": "Sujet de l'email"
                        },
                        "corps": {
                            "type": "string",
                            "description": "Corps du message"
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    async def executer_args(self, action, destinataire=None, sujet=None, corps=None):
        if action == "envoyer":
            return "Pour envoyer un email, confirme le destinataire, le sujet et le message."
        if action == "lire":
            return "Fonction lecture emails pas encore connectée à un compte IMAP."
        return "Email: action non reconnue."
