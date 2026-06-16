# MimoBot - Agent AI Personnel

Agent AI modulaire et extensible pour Telegram. Utilise Groq (llama-3.3-70b) avec fallback Gemini (gemini-2.0-flash).

## Stack

- **Langage**: Python
- **LLM**: Groq + Gemini
- **Memoire**: Firebase Firestore
- **Auth/Storage**: Supabase
- **Interface**: Telegram Bot
- **Hebergement**: PythonAnywhere

## Installation

```bash
git clone https://github.com/ton-compte/mimo-bot.git
cd mimo-bot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Remplir .env avec tes cles API
python telegram/bot.py
```

## Deploiement sur PythonAnywhere

1. Ouvre PythonAnywhere et va dans **Files**
2. Upload tout le dossier `mon-agent/`
3. Va dans **Consoles** → **Bash console**
4. Execute :
   ```bash
   cd mon-agent
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
5. Va dans **Web** → **Add a new web app**
   - Choisis **Manual configuration** → **Python 3.10**
6. Dans **Code** :
   - Source code: `/home/ton_user/mon-agent`
   - Working directory: `/home/ton_user/mon-agent`
   - WSGI file: cree un fichier pointant vers `telegram/bot.py`
7. Dans **Tasks** → ajoute une **Always-on task** :
   ```bash
   cd /home/ton_user/mon-agent && python telegram/bot.py
   ```

## Commandes Telegram

- `/start` - Demarrer
- `/help` - Aide
- `/outils` - Liste des outils
- `/status` - Etat de l'agent
- `/memoire` - Profil memorise
- `/installer <package>` - Installer un outil

## Structure

```
mon-agent/
  core/          # Cerveau (agent, llm, memoire, router)
  tools/         # Outils (calendrier, email, correction, etc.)
  skills/        # Competences (recherche web, auto-install)
  telegram/      # Bot Telegram
  config/        # Configuration
```
