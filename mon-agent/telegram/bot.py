import os, sys, time, asyncio, logging, threading, json
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
LLM_INDICATEURS = {"groq": "llama-3.3-70b", "gemini": "gemini-2.0-flash"}

def get_agent():
    global agent
    if agent is None:
        agent = Agent()
    return agent

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nom = get_agent().config["agent"]["nom"]
    await update.message.reply_text(f"Bonjour ! Je suis {nom}.\nUtilise /help pour les commandes.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - Demarrer\n/help - Aide\n/outils - Outils\n/status - Etat\n/memoire - Profil")

async def outils(update: Update, context: ContextTypes.DEFAULT_TYPE):
    a = get_agent()
    lignes = ["**Outils actifs :**"]
    for nom in a.outils:
        lignes.append(f"- {nom}")
    lignes.append(f"\n**LLM principal:** {a.config['llm']['modele_groq']}")
    await update.message.reply_text("\n".join(lignes))

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    a = get_agent()
    llm = LLM_INDICATEURS.get(a.llm.llm_actif, a.llm.llm_actif)
    await update.message.reply_text(f"**{a.config['agent']['nom']}**\nVersion: {a.config['agent']['version']}\nLLM: {llm}\nMemoire: {len(a.memory.court_terme)} messages\nOutils: {len(a.outils)}")

async def memoire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    a = get_agent()
    profil = a.memory.charger_profil(str(update.effective_user.id))
    prefs = profil.get("preferences", {})
    await update.message.reply_text(f"**Profil**\nLangue: {prefs.get('langue', 'fr')}\nMessages session: {len(a.memory.court_terme)}")

async def installer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    package = " ".join(context.args) if context.args else ""
    if not package:
        await update.message.reply_text("Usage: /installer <nom_package>")
        return
    outil = get_agent().outils.get("auto_install")
    if not outil:
        await update.message.reply_text("Outil indisponible.")
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
        log.error(f"Erreur: {e}")
        await update.message.reply_text("Desole, une erreur s'est produite.")

class SanteHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *a): pass

def keepalive():
    import httpx
    while True:
        time.sleep(300)
        try:
            httpx.get(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_TOKEN')}/getMe", timeout=10)
            log.info("Keepalive OK")
        except Exception as e:
            log.warning(f"Keepalive: {e}")

def lancer_bot():
    global agent
    agent = None
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        log.error("TELEGRAM_TOKEN manquant")
        return
    app = Application.builder().token(token).build()
    for h in [CommandHandler("start", start), CommandHandler("help", help_command),
              CommandHandler("outils", outils), CommandHandler("status", status),
              CommandHandler("memoire", memoire), CommandHandler("installer", installer),
              MessageHandler(filters.TEXT & ~filters.COMMAND, repondre_message)]:
        app.add_handler(h)
    log.info("MimoBot demarre...")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message"])

def main():
    port = int(os.environ.get("PORT", 10000))
    t_http = threading.Thread(target=HTTPServer(("0.0.0.0", port), SanteHandler).serve_forever, daemon=True)
    t_http.start()
    t_keep = threading.Thread(target=keepalive, daemon=True)
    t_keep.start()
    time.sleep(2)
    while True:
        try:
            lancer_bot()
        except Exception as e:
            log.error(f"Bot error: {e}")
        log.info("Redemarrage dans 5s...")
        time.sleep(5)

if __name__ == "__main__":
    main()
