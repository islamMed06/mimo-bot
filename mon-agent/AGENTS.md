# MimoBot — Analyse du projet

## Architecture
```
mon-agent/
├── config/config.json              ← Configuration centralisee
├── core/
│   ├── agent.py                    ← Ordonnanceur : function calling + fallback router
│   ├── llm.py                      ← Multi-LLM (Groq→Gemini→OpenRouter→...) + temps HTTP
│   ├── memory.py                   ← Memoire court-terme (dict par user) + Firebase long-terme
│   └── router.py                   ← Keyword router (fallback)
├── skills/built_in/                ← Competences (rappel, meteo, traducteur, recherche, etc.)
├── tools/built_in/                 ← Outils internes (site_web)
├── telegram/
│   ├── bot.py                      ← Handlers Telegram + HTTP health server + rappels
│   └── monitor.py                  ← Keepalive + heartbeat
├── firestore.indexes.json          ← Index composite reminders
└── tests/                          ← 49 tests pytest

## Pile technique
- LLM primaire: Groq `openai/gpt-oss-120b` (120B, 131K ctx, gratuit)
- Fallback: Gemini 2.0-flash → OpenRouter → HF → Cloudflare → GitHub
- Base: Firebase Firestore (profils, conversations, reminders)
- Mapping user: Supabase
- Hebergement: Render (gratuit, redemarrage ~00:00 Algerie)
- Messagerie: Telegram Bot API (python-telegram-bot v22+)
- Temps: HTTP Date header via urllib (evite Python 3.14 `fromtimestamp` bug)

## Corrections effectuees

### Critiques (1-7)
1. `court_terme` liste unique → dict[str, list] partitionne par user_id
2. Race condition Firestore → @firestore.transactional
3. `contenu[:500]` sans log → log.warning si > 500
4. `fromisoformat` naive → TypeError → ts.replace(tzinfo=ALGERIA_TZ)
5. `supprimer_rappel`/`marquer_envoye` ignorent user_id → verification propriete
6. Compression 5 en dur → court_terme_max
7. SyntaxError do_GET → deja corrige

### Majeurs (8-15)
8. `rappels_echus` scanne tous les users → limit(100)
9. `compter_sessions` charge tous les docs → select([])
10. limit(2) en dur → max(1, min(10, limit//20))
11. Collision doc_id → uuid4().hex (deja A4)
12. reponde tools: reponse="" possible → if texte: au lieu de if msg:
13. Aucune limite appels outils → iterations < 3 (deja A5)
14. `_restaurer_contexte` synchrone → async + asyncio.to_thread()
15. LLM_INDICATEURS hardcode → noms_affichage dans config.json (deja A9)

## Tests
49 tests, 0 echec:
- test_memory.py: ProfileCache (hit, miss, TTL, invalidation)
- test_router.py: Detection intention + mapping execution
- test_rappel.py: Extraction duree/message, formatage
- test_meteo.py: Extraction ville (prepositions, stop words)
- test_traducteur.py: Analyse source/cible, guillemets
- test_agent.py: Orchestration traiter_message (fallback, tool_calls, iterations, auto-name, partition, empty response, contexte, identite) ✅ nouveau
- test_llm.py: LLMManager (time bypass, tool_calls format, empty fallback, fallback chain, system prompt, resume anciens) ✅ nouveau

## Risques residuels
- Render redemarrage ~00:00 → perte memoire court-terme (restaure depuis Firebase)
- `gc.collect()` apres chaque LLM (empirique)

## Prochaines etapes recommandees
1. Tests integration: mock Firestore + mock Groq pour traiter_message() ✅ fait (49 tests, 14 nouveaux)
2. Ajouter cles API HF + Cloudflare sur Render ✅ fait (local + prod)
3. Migration google.generativeai → google.genai (deprecation FutureWarning) ✅ fait
4. Creer index compose Firestore: reminders envoye ASC, timestamp ASC ✅ fait (en cours de build)
5. Differer `_extraire_identite` (appel Groq couteux synchrone) ✅ fait (asyncio.to_thread)
6. Phase 3: Site Next.js (Vercel) pour cours d'anglais
7. Phase 4: Connexion agent ↔ site via API secret partage
