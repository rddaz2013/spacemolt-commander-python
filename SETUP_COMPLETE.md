# 🚀 SpaceMolt Commander Setup — Complete Documentation

**Datum:** Mai 17, 2026  
**Version:** 1.0  
**Repository:** https://github.com/rddaz2013/spacemolt-commander-python

---

## 📚 Erstellte Dokumentation

Diese detaillierte Anleitung zur Einrichtung der Credentials für den SpaceMolt Commander umfasst folgende Dateien:

### 1. **QUICK_START.md** — Schnelleinstieg (5 Minuten)
   - Interaktives Setup mit `python setup_config.py`
   - Manuelle Konfiguration
   - API-Key Generierung
   - Häufige Szenarien
   - **Zielgruppe:** Anfänger

### 2. **CREDENTIALS_SETUP.md** — Ausführliche Anleitung (30 Minuten)
   - SpaceMolt API Credentials
   - Cloud LLM Backend Optionen (Claude, GPT-4, Groq, Abacus.AI)
   - Lokale Ollama-Modelle Setup
   - Umgebungsvariablen Konfiguration
   - Troubleshooting & Sicherheit
   - **Zielgruppe:** Fortgeschrittene Benutzer

### 3. **config.reference.yaml** — Konfigurationsvorlagen
   - 8 verschiedene Presets für unterschiedliche Anwendungsfälle:
     - Preset 1: Best Overall (Hybrid Cloud + Local)
     - Preset 2: Cloud Only (Maximum Quality)
     - Preset 3: Local Only (Free & Private)
     - Preset 4: High-Reasoning Focus
     - Preset 5: Budget (Groq Free)
     - Preset 6: Abacus.AI Integration
     - Preset 7: Multiple Sessions
     - Preset 8: Debug & Development
   - **Zielgruppe:** Alle

### 4. **.env.example** — Environment-Variablen Template
   - Sichere Verwaltung von API-Keys
   - Platzhalter für alle unterstützten Services
   - Best Practices & Security-Tipps
   - **Zielgruppe:** Alle (besonders Sicherheitsbewusste)

### 5. **setup_config.py** — Interaktives Setup-Script
   - Geführter Konfigurationsprozess
   - Automatische Erkennung von Ollama
   - API-Key Validierung
   - Erstellt automatisch `config.yaml`
   - Farbcodierte Ausgabe
   - **Ausführung:** `python setup_config.py`

### 6. **SETUP_COMPLETE.md** — Diese Datei
   - Übersicht aller Dokumentation
   - Nächste Schritte
   - Quick Reference

---

## 🎯 Erste Schritte (Wähle einen Pfad)

### Option A: Interaktives Setup (empfohlen für Anfänger)

```bash
cd /home/ubuntu/spacemolt_commander_python
python setup_config.py
```

Das Script wird dich durch folgende Punkte führen:
1. SpaceMolt API Credentials
2. Cloud LLM Auswahl
3. Lokale Ollama-Modelle (optional)
4. Mission Definition
5. Automatische Erstellung von `config.yaml`

**Dauer:** ~5 Minuten  
**Schwierigkeit:** ⭐ Einfach

---

### Option B: Manuelle Konfiguration (für Experten)

```bash
# 1. Kopiere Template
cp config.example.yaml config.yaml

# 2. Editiere mit deinem Editor
nano config.yaml

# 3. Setze API-Keys
export ANTHROPIC_API_KEY="sk-ant-..."

# 4. Führe aus
python -m spacemolt run "Your mission"
```

**Dauer:** ~10 Minuten  
**Schwierigkeit:** ⭐⭐ Mittel

---

### Option C: Preset-Auswahl (für Spezialisten)

```bash
# 1. Wähle ein Preset aus config.reference.yaml
# 2. Kopiere in config.yaml
# 3. Passe deine API-Keys an
# 4. Fertig!
```

**Dauer:** ~5 Minuten  
**Schwierigkeit:** ⭐⭐⭐ Fortgeschritten

---

## 🔑 API-Keys Checkliste

Abhängig von deinem gewählten Backend benötigst du:

### Für Cloud-Modelle

- **Anthropic Claude** (empfohlen)
  - [ ] API Key von https://console.anthropic.com/
  - [ ] `export ANTHROPIC_API_KEY="sk-ant-..."`

- **OpenAI GPT-4**
  - [ ] API Key von https://platform.openai.com/api-keys
  - [ ] `export OPENAI_API_KEY="sk-..."`

- **Groq** (kostenlos)
  - [ ] API Key von https://console.groq.com/keys
  - [ ] `export GROQ_API_KEY="gsk_..."`

- **Abacus.AI** (falls Abo)
  - [ ] API Key von https://abacus.ai/app/account
  - [ ] `export ABACUS_API_KEY="..."`

### Für Lokale Modelle

- **Ollama** (kostenlos)
  - [ ] Installiert von https://ollama.ai
  - [ ] Server läuft mit `ollama serve`
  - [ ] Modell heruntergeladen: `ollama pull qwen3:8b`

### Für SpaceMolt API

- **SpaceMolt**
  - [ ] Account registriert auf https://game.spacemolt.com
  - [ ] API Key generiert
  - [ ] Wird beim ersten Run abgefragt

---

## 🎮 Erste Mission Ausführen

Nach dem Setup kannst du sofort spielen:

```bash
# Einzelne Mission
python -m spacemolt run "Überprüfe meinen Spielzustand"

# Service-Mode (kontinuierlich)
python -m spacemolt service --mission "Mine ore and trade"

# Mit spezifischer Session
python -m spacemolt run "Your mission" --session my-bot

# Mit Debug-Ausgabe
python -m spacemolt run "Your mission" --debug

# Mit Force-Credentials (neue Anmeldung)
python -m spacemolt run "Your mission" --force-credentials
```

---

## 📊 Konfigurationsübersicht

| Feld | Beispiel | Beschreibung |
|------|----------|-------------|
| `cloud_model` | `anthropic/claude-sonnet-4-20250514` | Modell für komplexe Aufgaben |
| `local_model` | `ollama/qwen3:8b` | Modell für einfache Aufgaben |
| `api_url` | `https://game.spacemolt.com/api/v2` | SpaceMolt API Endpoint |
| `session_name` | `default` | Eindeutige Session-ID |
| `mission` | `"Mine ore and get rich"` | Langfristige Anweisung |
| `backend` | `auto` | Backend-Strategie (auto/local/cloud) |
| `debug` | `false` | Ausführliches Logging? |

---

## 💡 Backend-Auswahl Guide

### 🟢 Anfänger → Nutze Preset 1 (Hybrid)

```yaml
backend: "auto"
cloud_model: "anthropic/claude-sonnet-4-20250514"
local_model: "ollama/qwen3:8b"
```

**Warum:** Balance zwischen Qualität und Kosten. Best Practice.

---

### 💰 Budget → Nutze Preset 3 (Local)

```yaml
backend: "local"
local_model: "ollama/qwen3:8b"
```

**Warum:** Komplett kostenlos, schnell, genug für die meisten Aufgaben.

---

### 🚀 Max Performance → Nutze Preset 2 (Cloud)

```yaml
backend: "cloud"
cloud_model: "anthropic/claude-sonnet-4-20250514"
```

**Warum:** Beste Strategische Planung und Entscheidungen.

---

## 🐛 Häufige Probleme

### "Ollama not found"
```bash
# Installiere Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen3:8b
ollama serve  # In separatem Terminal
```

### "API Key invalid"
```bash
# Überprüfe ob gesetzt
echo $ANTHROPIC_API_KEY

# Oder generiere neuen Key
# https://console.anthropic.com/
```

### "Connection to SpaceMolt failed"
```bash
# Überprüfe URL
curl https://game.spacemolt.com/api/v2/

# Überprüfe API-Key (beim nächsten Run)
python -m spacemolt run "test" --force-credentials
```

**Mehr Lösungen:** Siehe `CREDENTIALS_SETUP.md` → Troubleshooting

---

## 📁 Projektstruktur

```
spacemolt_commander_python/
├── README.md                          # Projekt-Info
├── SETUP_COMPLETE.md                  # ← Diese Datei
├── QUICK_START.md                     # Schnelleinstieg
├── CREDENTIALS_SETUP.md               # Ausführliche Anleitung
├── config.example.yaml                # Beispiel-Konfiguration
├── config.reference.yaml              # Konfigurationsvorlagen
├── config.yaml                        # ← DEINE Konfiguration (gitignored)
├── .env.example                       # Environment-Variablen Template
├── setup_config.py                    # Interaktives Setup-Script
├── requirements.txt                   # Python Dependencies
├── pyproject.toml                     # Projekt-Metadaten
└── spacemolt/
    ├── __init__.py
    ├── cli.py                         # CLI Einstiegspunkt
    ├── commander.py                   # Haupt-Agent
    ├── llm_router.py                  # LLM-Routing-Logik
    ├── api.py                         # SpaceMolt API-Client
    ├── models.py                      # Datenmodelle
    ├── session.py                     # Session-Management
    ├── schema.py                      # API Schemas
    ├── tools.py                       # Tool-Definitionen
    ├── code_executor.py               # Code-Ausführung
    ├── compaction.py                  # Speicheroptimierung
    ├── loop.py                        # Agentenloop
    ├── prompt.md                      # System Prompt
    └── ui.py                          # UI/Logging
```

---

## 🔐 Sicherheit Tipps

1. **Niemals API-Keys in Git committen**
   ```bash
   echo "config.yaml" >> .gitignore
   echo ".env" >> .gitignore
   ```

2. **Umgebungsvariablen verwenden**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

3. **Regelmäßig Keys rotieren**
   - Alle 3 Monate neue Keys generieren
   - Alte Keys löschen

4. **Credentials sichern**
   ```bash
   tar -czf backup.tar.gz ~/.spacemolt_commander/
   ```

---

## 📚 Dokumentationen Übersicht

| Datei | Länge | Zielgruppe | Inhalt |
|-------|-------|-----------|--------|
| QUICK_START.md | 1-2 Seiten | Anfänger | 5-Min Setup |
| CREDENTIALS_SETUP.md | 5-10 Seiten | Fortgeschritten | Details |
| config.reference.yaml | 1-2 Seiten | Alle | 8 Presets |
| .env.example | 1 Seite | Alle | Env-Vars |
| setup_config.py | Script | Anfänger | Auto-Setup |

---

## ✅ Checkliste für erfolgreichen Start

- [ ] Abhängigkeiten installiert: `pip install -r requirements.txt`
- [ ] `config.yaml` erstellt (automatisch oder manuell)
- [ ] API-Key für Cloud-Modell gesetzt (z.B. `export ANTHROPIC_API_KEY=...`)
- [ ] Optional: Ollama installiert und läuft (falls lokale Modelle)
- [ ] Erste Mission getestet: `python -m spacemolt run "test"`
- [ ] Session-Status überprüft: `python -m spacemolt status`

---

## 🎓 Nächste Schritte

### Sofort (5 Minuten)
1. Setup-Script ausführen: `python setup_config.py`
2. API-Keys setzen
3. Test-Mission ausführen

### Kurzfristig (30 Minuten)
1. Mission-Parameter optimieren
2. Backend-Strategie testen
3. Logs überprüfen

### Langfristig
1. Mehrere Sessions für verschiedene Strategien
2. Performance-Monitoring
3. Mission-Anpassung basierend auf Ergebnissen

---

## 🆘 Support

### Dokumentation
- **Quick Start:** `QUICK_START.md`
- **Detailliert:** `CREDENTIALS_SETUP.md`
- **Konfigurationen:** `config.reference.yaml`

### Online
- **SpaceMolt:** https://game.spacemolt.com
- **Repository:** https://github.com/rddaz2013/spacemolt-commander-python
- **Anthropic Docs:** https://docs.anthropic.com
- **Ollama:** https://ollama.ai/library

### Lokale Hilfe
```bash
# CLI-Hilfe
python -m spacemolt --help
python -m spacemolt run --help
python -m spacemolt service --help
python -m spacemolt status --help

# Debug Mode
python -m spacemolt run "Your mission" --debug
```

---

## 📝 Lizenz & Attribution

**SpaceMolt Commander**  
- Repository: https://github.com/rddaz2013/spacemolt-commander-python
- Setup-Dokumentation: Erstellt 17. Mai 2026
- Lizenz: Siehe Repository

**Abhängigkeiten:**
- Anthropic Claude (über litellm)
- OpenAI GPT (über litellm)
- Groq (über litellm)
- Ollama (lokal)
- Abacus.AI (optional)

---

## 🎉 Fertig!

Du hast jetzt alles, was du brauchst, um den SpaceMolt Commander zu starten!

```bash
# Wähle einen Weg:
python setup_config.py       # Interaktives Setup
# oder
python -m spacemolt run "Mine ore!"  # Direkt starten
```

**Viel Erfolg! 🚀**

---

*Dokumentation erstellt mit ❤️ für SpaceMolt Commander*
