import os, sys, time, logging, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from core.agent import Agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger("BOT")

HEARTBEAT_FILE = os.path.join(os.path.dirname(__file__), "..", "heartbeat.txt")
agent = None
START_TIME = time.time()
POLL_COUNT = 0
LLM_INDICATEURS = {"groq": "llama-3.1-8b", "gemini": "gemini-2.0-flash", "openrouter": "llama-3.3-70b", "huggingface": "phi-3", "cloudflare": "llama-3.2-3b", "github": "gpt-4o-mini"}

def get_agent():
    global agent
    if agent is None:
        agent = Agent()
    return agent

def heartbeat():
    while True:
        time.sleep(10)
        try:
            with open(HEARTBEAT_FILE, "w") as f:
                f.write(str(time.time()))
        except Exception:
            pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nom = get_agent().config["agent"]["nom"]
    await update.message.reply_text(f"Bonjour ! Je suis {nom}.\nUtilise /help pour les commandes.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - Demarrer\n/help - Aide\n/outils - Outils\n/status - Etat\n/uptime - Temps actif\n/diagnostic - Diagnostique\n/test_llm - Test LLM\n/memoire - Profil")

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
    upt = int(time.time() - START_TIME)
    h, r = divmod(upt, 3600); m, s = divmod(r, 60)
    await update.message.reply_text(f"**{a.config['agent']['nom']}** v{a.config['agent']['version']}\nLLM: {llm}\nUptime: {h}h{m:02d}m\nRedemarrages: {POLL_COUNT}\nMemoire: {len(a.memory.court_terme)} msgs\nOutils: {len(a.outils)}")

async def diagnostic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    a = get_agent()
    lignes = ["**Diagnostic MimoBot**"]
    for var in ["GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "HF_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "GITHUB_TOKEN", "FIREBASE_PRIVATE_KEY"]:
        lignes.append(f"{var}: {'✅' if os.getenv(var) else '❌'}")
    erreurs = [f"{n}={getattr(a.llm, f'derniere_erreur_{n}', 'ok')}" for n in ["groq", "gemini", "openrouter", "huggingface", "cloudflare", "github"]]
    lignes.append(f"LLM actif: {a.llm.llm_actif}")
    lignes.append(f"Erreurs: {' | '.join(erreurs)}")
    lignes.append(f"Historique: {len(a.llm.historique)} msgs | Memoire: {len(a.memory.court_terme)} msgs")
    await update.message.reply_text("\n".join(lignes))

async def memoire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    a = get_agent()
    profil = a.memory.charger_profil(str(update.effective_user.id))
    prefs = profil.get("preferences", {})
    await update.message.reply_text(f"**Profil**\nLangue: {prefs.get('langue', 'fr')}\nMessages session: {len(a.memory.court_terme)}")

async def test_llm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    a = get_agent()
    msg = await update.message.reply_text("Test de tous les LLM...")
    test_msg = [{"role": "user", "content": "reponds 'ok' en 1 mot"}]
    resultats = []
    for nom, methode in [("Groq", a.llm._appeler_groq), ("Gemini", a.llm._appeler_gemini),
                          ("OpenRouter", a.llm._appeler_openrouter), ("HuggingFace", a.llm._appeler_huggingface),
                          ("Cloudflare", a.llm._appeler_cloudflare), ("GitHub", a.llm._appeler_github)]:
        try:
            r = methode(test_msg)
            if r:
                resultats.append(f"✅ {nom}: {r[:50]}")
            else:
                erreur = getattr(a.llm, f"derniere_erreur_{nom.lower()}", "inconnue")
                resultats.append(f"❌ {nom}: {erreur[:100]}")
        except Exception as e:
            resultats.append(f"❌ {nom}: {type(e).__name__}: {str(e)[:100]}")
    await msg.edit_text("\n".join(resultats))

async def uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upt = int(time.time() - START_TIME)
    h, r = divmod(upt, 3600); m, s = divmod(r, 60)
    d, h2 = divmod(h, 24)
    if d:
        await update.message.reply_text(f"Actif depuis {d}j {h2}h{m:02d}m{s:02d}s")
    else:
        await update.message.reply_text(f"Actif depuis {h}h{m:02d}m{s:02d}s")

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

def lancer_bot():
    global agent, POLL_COUNT
    agent = None
    POLL_COUNT += 1
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        log.error("TELEGRAM_TOKEN manquant")
        return
    import httpx
    httpx.post(f"https://api.telegram.org/bot{token}/deleteWebhook", timeout=5)
    httpx.post(f"https://api.telegram.org/bot{token}/close", timeout=5)
    time.sleep(2)
    app = Application.builder().token(token).build()
    handlers = [CommandHandler("start", start), CommandHandler("help", help_command),
                CommandHandler("outils", outils), CommandHandler("status", status),
                CommandHandler("diagnostic", diagnostic), CommandHandler("test_llm", test_llm),
                CommandHandler("uptime", uptime),
                CommandHandler("memoire", memoire), CommandHandler("installer", installer),
                MessageHandler(filters.TEXT & ~filters.COMMAND, repondre_message)]
    for h in handlers:
        app.add_handler(h)
    log.info("MimoBot demarre...")
    try:
        app.run_polling(drop_pending_updates=True, allowed_updates=["message"], bootstrap_retries=3)
    except Exception as e:
        log.error(f"Polling arrete: {type(e).__name__}: {e}")

if __name__ == "__main__":
    t_heart = threading.Thread(target=heartbeat, daemon=True)
    t_heart.start()
    lancer_bot()
