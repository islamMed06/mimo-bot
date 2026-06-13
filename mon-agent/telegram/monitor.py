import os, sys, time, subprocess, logging, threading
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger("MONITOR")

HEARTBEAT_FILE = os.path.join(os.path.dirname(__file__), "..", "heartbeat.txt")
BOT_SCRIPT = os.path.join(os.path.dirname(__file__), "bot.py")

class SanteHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *a): pass

def start_bot():
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    log.info("Demarrage du sous-processus bot...")
    return subprocess.Popen(
        [sys.executable, "-u", BOT_SCRIPT],
        env=env,
        cwd=os.path.dirname(BOT_SCRIPT),
        stdout=sys.stdout,
        stderr=sys.stderr
    )

def surveiller():
    import httpx
    bot = None
    while True:
        time.sleep(15)
        try:
            r = httpx.get(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_TOKEN')}/getMe", timeout=10)
            if r.status_code == 200:
                log.info("Keepalive OK")
        except Exception as e:
            log.warning(f"Keepalive: {e}")
        if bot and bot.poll() is not None:
            log.warning(f"Bot termine (code {bot.returncode}), redemarrage...")
            bot = start_bot()
            continue
        if bot:
            try:
                with open(HEARTBEAT_FILE, "r") as f:
                    ts = float(f.read().strip())
                age = int(time.time() - ts)
                if age > 60:
                    log.warning(f"Bot freeze detecte (heartbeat age={age}s), kill et redemarrage...")
                    bot.kill()
                    bot.wait(5)
                    bot = start_bot()
            except (FileNotFoundError, ValueError):
                pass
        if bot is None:
            bot = start_bot()

def main():
    port = int(os.environ.get("PORT", 10000))
    t_http = threading.Thread(target=lambda: HTTPServer(("0.0.0.0", port), SanteHandler).serve_forever(), daemon=True)
    t_http.start()
    log.info("Moniteur demarre, port " + str(port))
    surveiller()

if __name__ == "__main__":
    main()
