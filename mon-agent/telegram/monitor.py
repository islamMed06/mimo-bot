import os, sys, time, subprocess, logging, threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger("MONITOR")

HEARTBEAT_FILE = os.path.join(os.path.dirname(__file__), "..", "heartbeat.txt")
BOT_SCRIPT = os.path.join(os.path.dirname(__file__), "bot.py")

def start_bot():
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    log.info("Demarrage du sous-processus bot...")
    return subprocess.Popen(
        [sys.executable, "-u", BOT_SCRIPT],
        env=env,
        cwd=os.path.dirname(BOT_SCRIPT)
    )

def surveiller():
    import httpx
    bot = None
    token = os.getenv("TELEGRAM_TOKEN")
    while True:
        time.sleep(15)
        if token:
            try:
                r = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
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
                if age > 120:
                    log.warning(f"Bot freeze (heartbeat age={age}s), redemarrage...")
                    bot.kill()
                    bot.wait(5)
                    bot = start_bot()
            except (FileNotFoundError, ValueError):
                pass
        if bot is None:
            bot = start_bot()

if __name__ == "__main__":
    log.info("Moniteur demarre...")
    try:
        surveiller()
    except KeyboardInterrupt:
        log.info("Arret demande")
