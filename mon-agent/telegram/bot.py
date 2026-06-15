import os, sys, time, logging, threading, gc, atexit, signal
from http.server import HTTPServer, BaseHTTPRequestHandler

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
_agent_lock = threading.Lock()
START_TIME = time.time()
POLL_COUNT = 0
_TOKEN = os.getenv("TELEGRAM_TOKEN")
_STOP = False

def _fermer_session():
    import httpx
    if _TOKEN:
        try:
            httpx.post(f"https://api.telegram.org/bot{_TOKEN}/close", timeout=5)
        except Exception:
            pass

atexit.register(_fermer_session)

def _stopper(signum, frame):
    global _STOP
    _STOP = True
    log.info("SIGTERM recu, sortie propre...")

signal.signal(signal.SIGTERM, _stopper)
LLM_INDICATEURS = {"groq": "llama-3.1-8b", "gemini": "gemini-2.0-flash", "openrouter": "llama-3.3-70b", "huggingface": "phi-3", "cloudflare": "llama-3.2-3b", "github": "gpt-4o-mini"}

def get_agent():
    global agent, _agent_lock
    with _agent_lock:
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
    user_id = str(update.effective_user.id)
    lignes = ["**Diagnostic MimoBot**"]
    for var in ["GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "HF_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "GITHUB_TOKEN", "FIREBASE_PRIVATE_KEY"]:
        lignes.append(f"{var}: {'✅' if os.getenv(var) else '❌'}")
    fb_status = "✅ connecte" if a.memory.db is not None else "❌ NON connecte"
    lignes.append(f"Firebase DB: {fb_status}")
    if a.memory.db:
        fb_test = a.memory.test_lecture_ecriture(user_id)
        lignes.append(f"Firebase test: {fb_test}")
    # Restaurer le contexte si necessaire pour le diagnostic
    if not a.llm.historique:
        a._restaurer_contexte(user_id)
    h_len = len(a.llm.historique)
    sessions_fb = a.memory.compter_sessions(user_id) if a.memory.db else "N/A"
    lignes.append(f"User: {user_id} | Hist: {h_len} msgs | Sessions FB: {sessions_fb}")
    erreurs = [f"{n}={getattr(a.llm, f'derniere_erreur_{n}', 'ok')}" for n in ["groq", "gemini", "openrouter", "huggingface", "cloudflare", "github"]]
    lignes.append(f"LLM actif: {a.llm.llm_actif}")
    lignes.append(f"Erreurs: {' | '.join(erreurs)}")
    if h_len > 0:
        lignes.append(f"Dernier msg hist: {a.llm.historique[-1].get('content', '')[:100]}")
    # Verifier si le resume est dans l'historique
    resumes = [m for m in a.llm.historique if m["role"] == "system" and "Resume" in m["content"]]
    lignes.append(f"Resumes dans hist: {len(resumes)}")
    for r in resumes:
        lignes.append(f"  -> {r['content'][:120]}")
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
    envoyer_rappels()
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

def keepalive():
    import httpx
    port = int(os.environ.get("PORT", 10000))
    counter = 0
    log.info("Keepalive demarre (verifie rappels toutes les 15s)")
    while True:
        time.sleep(15)
        counter += 1
        envoyer_rappels()
        if counter % 8 == 0:
            try:
                httpx.get(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_TOKEN')}/getMe", timeout=10)
            except Exception:
                pass
            try:
                httpx.get(f"http://localhost:{port}", timeout=5)
            except Exception:
                pass
            gc.collect()

def envoyer_rappels():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        return
    try:
        a = get_agent()
        if not a.memory.db:
            return
        echus = a.memory.rappels_echus()
        if not echus:
            return
        log.info(f"Envoi de {len(echus)} rappel(s)")
        import httpx
        for r in echus:
            try:
                resp = httpx.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": r["user_id"], "text": f"Rappel : {r['message']}"},
                    timeout=10
                )
                if resp.status_code == 200:
                    a.memory.marquer_envoye(r["user_id"], r["doc_id"])
                    log.info(f"Rappel envoye a {r['user_id']}: {r['message'][:40]}")
            except Exception as e:
                log.warning(f"Envoi rappel: {e}")
    except Exception as e:
        log.warning(f"Scheduler rappels: {type(e).__name__}: {e}")

class SanteHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        envoyer_rappels()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *a): pass

def lancer_bot():
    global agent, POLL_COUNT
    agent = None
    POLL_COUNT += 1
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        log.error("TELEGRAM_TOKEN manquant")
        return
    import httpx
    # Clean up any stale polling sessions before starting
    for t in range(3):
        try:
            r = httpx.post(f"https://api.telegram.org/bot{token}/close", timeout=5)
            if r.status_code in (200, 429):
                if r.status_code == 200:
                    log.info(f"Session fermee (tentative {t+1})")
                break
            time.sleep(2)
        except Exception:
            time.sleep(2)
    httpx.post(f"https://api.telegram.org/bot{token}/deleteWebhook", timeout=5)
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
    for t in range(4):
        try:
            app.run_polling(drop_pending_updates=True, allowed_updates=["message"], bootstrap_retries=3)
            break
        except Exception as e:
            err_str = f"{type(e).__name__}: {e}"
            log.error(f"Polling arrete: {err_str}")
            if "Conflict" in str(e) and t < 3:
                duree = 5 * (t + 1)
                log.info(f"Conflit detecte, retente dans {duree}s (tentative {t+1}/3)...")
                httpx.post(f"https://api.telegram.org/bot{token}/close", timeout=5)
                time.sleep(duree)
            else:
                break

def demarrer_http(port):
    from http.server import HTTPServer
    server = HTTPServer(("0.0.0.0", port), SanteHandler)
    server.serve_forever()

def main():
    port = int(os.environ.get("PORT", 10000))
    t_http = threading.Thread(target=demarrer_http, args=(port,), daemon=True)
    t_http.start()
    t_keep = threading.Thread(target=keepalive, daemon=True)
    t_keep.start()
    t_heart = threading.Thread(target=heartbeat, daemon=True)
    t_heart.start()
    time.sleep(2)
    global _STOP
    while not _STOP:
        try:
            lancer_bot()
        except Exception as e:
            log.error(f"Bot error: {e}")
        if _STOP:
            break
        log.info("Bot redemarrage dans 5s...")
        time.sleep(5)

if __name__ == "__main__":
    main()
