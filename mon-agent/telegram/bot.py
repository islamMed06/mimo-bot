import os
import sys
import time
import asyncio
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from core.agent import Agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger("BOT")

agent = None

LLM_INDICATEURS = {
    "groq": "llama-3.3-70b",
    "gemini": "gemini-2.0-flash"
}

def get_agent():
    global agent
    if agent is None:
        agent = Agent()
    return agent

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nom = get_agent().config["agent"]["nom"]
    await update.message.reply_text(
        f"Bonjour ! Je suis {nom}, ton assistant AI personnel.\n\n"
        f"Je peux t'aider a :\n"
        f"- Repondre a tes questions\n"
        f"- Gerer ton calendrier\n"
        f"- Corriger des exercices\n"
        f"- Gerer les notes des eleves\n"
        f"- Generer des fiches de lecons\n"
        f"- Controler ton site web\n"
        f"- Chercher des infos en ligne\n\n"
        f"Utilise /help pour voir les commandes disponibles."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Demarrer\n"
        "/help - Cette aide\n"
        "/outils - Liste des outils\n"
        "/status - Etat de l'agent\n"
        "/memoire - Ce que je sais de toi\n\n"
        "Tu peux aussi me parler naturellement en francais ou en anglais."
    )

async def outils(update: Update, context: ContextTypes.DEFAULT_TYPE):
    a = get_agent()
    lignes = ["**Outils actifs :**"]
    for nom, outil in a.outils.items():
        lignes.append(f"- {nom}")
    lignes.append("")
    lignes.append("**LLM :**")
    lignes.append(f"- Principal : {a.config['llm']['modele_groq']}")
    lignes.append(f"- Fallback : {a.config['llm']['modele_gemini']}")
    await update.message.reply_text("\n".join(lignes))

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    a = get_agent()
    llm = LLM_INDICATEURS.get(a.llm.llm_actif, a.llm.llm_actif)
    taille_memoire = len(a.memory.court_terme)
    await update.message.reply_text(
        f"**{a.config['agent']['nom']} - Status**\n\n"
        f"Version: {a.config['agent']['version']}\n"
        f"LLM actif: {llm}\n"
        f"Mode autonomie: {a.config['agent']['mode_autonomie']}\n"
        f"Memoire session: {taille_memoire} messages\n"
        f"Outils charges: {len(a.outils)}"
    )

async def memoire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    a = get_agent()
    profil = a.memory.charger_profil(str(update.effective_user.id))
    prefs = profil.get("preferences", {})
    await update.message.reply_text(
        f"**Ce que je sais de toi :**\n\n"
        f"Langue preferee: {prefs.get('langue', 'fr')}\n"
        f"Style reponse: {prefs.get('style_reponse', 'court')}\n"
        f"Messages session: {len(a.memory.court_terme)}"
    )

async def installer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    package = " ".join(context.args) if context.args else ""
    if not package:
        await update.message.reply_text("Usage: /installer <nom_package>")
        return
    outil = get_agent().outils.get("auto_install")
    if not outil:
        await update.message.reply_text("Outil d'installation non disponible.")
        return
    await update.message.reply_text(f"Installation de {package}...")
    resultat = await outil.installer(package)
    await update.message.reply_text(resultat)

async def repondre_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user_id = str(update.effective_user.id)
    texte = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        reponse, source = await get_agent().traiter_message(texte, user_id)
        llm_nom = LLM_INDICATEURS.get(source, source)
        if isinstance(reponse, str):
            await update.message.reply_text(reponse)
        elif isinstance(reponse, dict) and reponse.get("type") == "confirmation":
            msg = f"Action requise: {reponse['action']}\n"
            for k, v in reponse["donnees"].items():
                msg += f"{k}: {v}\n"
            msg += "\nConfirme avec 'oui' ou annule avec 'non'."
            context.user_data["action_attendue"] = reponse
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(str(reponse))
    except Exception as e:
        log.error(f"Erreur traitement message: {e}")
        await update.message.reply_text("Desole, une erreur s'est produite.")

class SanteHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"MimoBot OK")

    def log_message(self, format, *args):
        pass

def run_http():
    port = int(os.environ.get("PORT", 10000))
    serveur = HTTPServer(("0.0.0.0", port), SanteHandler)
    log.info(f"HTTP prêt sur le port {port}")
    serveur.serve_forever()

def lancer_bot():
    global agent
    agent = None
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        log.error("TELEGRAM_TOKEN manquant dans .env")
        return False
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("outils", outils))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("memoire", memoire))
    app.add_handler(CommandHandler("installer", installer))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, repondre_message))
    log.info("MimoBot demarre...")
    try:
        app.run_polling(drop_pending_updates=True, allowed_updates=["message"])
    except Exception as e:
        log.error(f"Erreur polling: {e}")
    return True

def main():
    t = threading.Thread(target=run_http, daemon=True)
    t.start()
    while True:
        try:
            lancer_bot()
        except Exception as e:
            log.error(f"Bot crashed: {e}")
        log.info("Redemarrage du bot dans 3 secondes...")
        time.sleep(3)

if __name__ == "__main__":
    main()
