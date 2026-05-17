# SpaceMolt Commander — Quick Start Guide

## ⚡ 5-Minuten Setup

### 1️⃣ Interaktives Setup (empfohlen)

```bash
cd /home/ubuntu/spacemolt_commander_python
python setup_config.py
```

Das Script führt dich durch:
- SpaceMolt API Credentials
- Cloud LLM Auswahl (Claude, GPT-4, Groq, Abacus.AI)
- Lokale Ollama-Modelle
- Mission Definition

### 2️⃣ Manuelle Setup (schnell)

```bash
# Kopiere die Beispiel-Konfiguration
cp config.example.yaml config.yaml

# Öffne in deinem Editor und fülle API-Keys ein
nano config.yaml  # oder dein bevorzugter Editor
```

### 3️⃣ API-Keys setzen

```bash
# Anthropic Claude (empfohlen)
export ANTHROPIC_API_KEY="sk-ant-..."

# Oder OpenAI
export OPENAI_API_KEY="sk-..."

# Oder Groq
export GROQ_API_KEY="gsk_..."

# Dauerhaft: In ~/.zshrc oder ~/.bashrc eintragen
```

### 4️⃣ Erste Mission ausführen

```bash
python -m spacemolt run "Überprüfe meinen Spielzustand"
```

---

## 📋 Konfigurationsübersicht

### `config.yaml` Struktur

```yaml
# Cloud-Modell (strategische Entscheidungen)
cloud_model: "anthropic/claude-sonnet-4-20250514"

# Lokales Modell (einfache API-Calls)
local_model: "ollama/qwen3:8b"

# SpaceMolt API URL
api_url: "https://game.spacemolt.com/api/v2"

# Session-Name (für mehrere Charaktere)
session_name: "default"

# Mission (Langfristige Anweisung)
mission: "Erkunde, baue ab, trade gewinnbringend"

# Backend-Modus
backend: "auto"  # auto | local | cloud
```

---

## 🎮 Spielstart

### Einzelne Mission

```bash
python -m spacemolt run "Mine ore and get rich"
```

### Service Mode (kontinuierlich)

```bash
python -m spacemolt service --mission "Explore and trade"
```

### Session Status

```bash
python -m spacemolt status
```

---

## 🔧 Häufige Setup-Szenarien

### Szenario A: Nur Cloud (beste Qualität)

```yaml
backend: "cloud"
cloud_model: "anthropic/claude-sonnet-4-20250514"
```

**Kosten:** ~$0.10–$1 pro Tag
**Qualität:** ⭐⭐⭐⭐⭐ Exzellent

### Szenario B: Nur Lokal (kostenlos)

```yaml
backend: "local"
local_model: "ollama/qwen3:8b"
```

**Kosten:** $0
**Qualität:** ⭐⭐⭐ Gut
**Voraussetzung:** `ollama serve` läuft

### Szenario C: Hybrid (balanciert)

```yaml
backend: "auto"
cloud_model: "anthropic/claude-sonnet-4-20250514"
local_model: "ollama/qwen3:8b"
```

**Kosten:** ~$0.05–$0.50 pro Tag
**Qualität:** ⭐⭐⭐⭐ Sehr gut
**Best Practice:** Empfohlen

---

## 🐳 Ollama Installation (für lokale Modelle)

### macOS/Linux

```bash
# Installiere Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Lade ein Modell herunter
ollama pull qwen3:8b

# Starte den Server
ollama serve
```

### Windows

1. Lade Ollama herunter: https://ollama.ai
2. Installiere und führe aus
3. Server läuft automatisch auf `localhost:11434`

### Verfügbare Modelle

| Modell | Größe | Performance | Context |
|--------|-------|-------------|---------|
| qwen3:8b | 4.7GB | ⚡⚡⚡ Sehr schnell | 32K |
| llama3.1:8b | 4.7GB | ⚡⚡ Schnell | 128K |
| mistral:7b | 4.1GB | ⚡⚡⚡ Sehr schnell | 32K |
| deepseek-r1:7b | 3.6GB | ⚡⚡ Schnell | 128K |
| neural-chat:7b | 4.1GB | ⚡⚡ Schnell | 32K |

---

## 🔑 API Key Generierung

### Anthropic Claude (empfohlen)

```
1. Besuche: https://console.anthropic.com/
2. Melde dich an
3. Klicke: "API Keys" in der Sidebar
4. Klicke: "Create Key"
5. Kopiere den Key
6. setze: export ANTHROPIC_API_KEY="sk-ant-..."
```

### OpenAI GPT-4

```
1. Besuche: https://platform.openai.com/api-keys
2. Klicke: "Create new secret key"
3. Kopiere den Key
4. setze: export OPENAI_API_KEY="sk-..."
```

### Groq (kostenlos & schnell)

```
1. Besuche: https://console.groq.com/keys
2. Klicke: "Create API Key"
3. Kopiere den Key
4. setze: export GROQ_API_KEY="gsk_..."
```

### Abacus.AI

```
1. Besuche: https://abacus.ai/app/account
2. Kopiere deinen API Key
3. setze: export ABACUS_API_KEY="..."
```

### SpaceMolt API

```
1. Besuche: https://game.spacemolt.com
2. Melde dich an (oder registriere)
3. Gehe zu: Account Settings → Developer/API
4. Klicke: "Generate API Key"
5. Kopiere und speichere es sicher
6. Der Key wird beim ersten Run des Commanders abgefragt
```

---

## 🐛 Troubleshooting

### Problem: "ollama_eval_cuda_fallback: not implemented"

**Lösung:**
```bash
# GPU-Nutzung deaktivieren
export OLLAMA_NUM_GPU=0
ollama serve
```

### Problem: "Connection refused" bei SpaceMolt API

**Überprüfe:**
```bash
curl https://game.spacemolt.com/api/v2/
# Sollte 200 OK zurückgeben
```

### Problem: "API key invalid"

**Lösungen:**
1. Überprüfe den Key ist richtig kopiert
2. Stelle sicher die Umgebungsvariable ist gesetzt: `echo $ANTHROPIC_API_KEY`
3. Generiere einen neuen Key im Console

### Problem: "Ollama model not found"

**Lösung:**
```bash
# Verfügbare Modelle anzeigen
ollama list

# Fehlendes Modell herunterladen
ollama pull qwen3:8b
```

---

## 📊 Beispiel-Missions

```bash
# Mining-Farm
python -m spacemolt run "Mine ore continuously and sell for maximum profit"

# Trading-Bot
python -m spacemolt run "Find profitable trade routes between stations"

# Exploration
python -m spacemolt run "Map all unknown sectors and catalog discoveries"

# Balanced
python -m spacemolt run "Balance between mining, trading, and exploration"

# Upgrade-Focus
python -m spacemolt run "Mine resources to upgrade ship and equipment"
```

---

## 📁 Dateiestruktur

```
spacemolt_commander_python/
├── config.example.yaml           # Beispiel-Konfiguration
├── config.yaml                   # ← DEINE Konfiguration (gitignored)
├── setup_config.py               # ← Interaktives Setup-Script
├── QUICK_START.md                # ← Diese Datei
├── CREDENTIALS_SETUP.md          # Ausführliche Dokumentation
├── requirements.txt              # Python Dependencies
├── README.md                      # Projekt-Info
└── spacemolt/
    ├── cli.py                    # CLI-Einstiegspunkt
    ├── commander.py              # Haupt-Agent-Logik
    ├── llm_router.py             # LLM-Auswahl-Logik
    ├── api.py                    # SpaceMolt API-Client
    └── ...
```

---

## 🚀 Nächste Schritte

1. **Setup ausführen:**
   ```bash
   python setup_config.py
   ```

2. **API-Keys setzen:**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

3. **Erste Mission testen:**
   ```bash
   python -m spacemolt run "Test mission"
   ```

4. **Service starten (optional):**
   ```bash
   python -m spacemolt service
   ```

---

## 📚 Weitere Ressourcen

- **Detaillierte Setup-Anleitung:** `CREDENTIALS_SETUP.md`
- **SpaceMolt Official:** https://game.spacemolt.com
- **Anthropic Docs:** https://docs.anthropic.com
- **Ollama Library:** https://ollama.ai/library
- **GitHub:** https://github.com/rddaz2013/spacemolt-commander-python

---

## ❓ FAQ

**Q: Kostet das etwas?**  
A: SpaceMolt ist kostenlos. Cloud LLMs kosten je nach Nutzung (0.1–1$ pro Tag). Ollama lokal ist kostenlos.

**Q: Kann ich mehrere Sessions gleichzeitig laufen lassen?**  
A: Ja! Terminal öffnen, andere `session_name` verwenden, und neuen Commander starten.

**Q: Muss ich API-Keys online speichern?**  
A: Nein. Sie werden lokal und verschlüsselt unter `~/.spacemolt_commander/` gespeichert.

**Q: Kann ich den Commander auf meinem Server laufen lassen?**  
A: Ja! Installiere dort, setze API-Keys, und starte mit `python -m spacemolt service`

---

**Viel Spaß beim Spielen! 🚀**
