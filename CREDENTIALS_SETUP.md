# SpaceMolt Commander — Credentials Setup Guide

Eine vollständige Anleitung zur Konfiguration des SpaceMolt Commander für den autonomen Spielbetrieb.

---

## 📋 Inhaltsverzeichnis

- [Quick Start](#quick-start)
- [Detaillierte Konfiguration](#detaillierte-konfiguration)
  - [SpaceMolt API Credentials](#spacemolt-api-credentials)
  - [LLM Backend Konfiguration](#llm-backend-konfiguration)
  - [Abacus.AI Integration (optional)](#abacusai-integration-optional)
  - [Lokale Ollama-Modelle](#lokale-ollama-modelle)
- [Konfigurationsdatei `config.yaml`](#konfigurationsdatei-configyaml)
- [LLM-Modelle Empfehlungen](#llm-modelle-empfehlungen)
- [Troubleshooting](#troubleshooting)
- [Sicherheit](#sicherheit)

---

## Quick Start

### 1. SpaceMolt Commander klonen oder cloned bereits vorhanden

```bash
cd /home/ubuntu/spacemolt_commander_python
```

### 2. Dependencies installieren

```bash
pip install -r requirements.txt
```

### 3. Konfigurationsdatei erstellen

```bash
cp config.example.yaml config.yaml
```

### 4. Credentials eintragen

Öffne `config.yaml` und fülle die erforderlichen API-Keys ein (siehe [Detaillierte Konfiguration](#detaillierte-konfiguration) weiter unten).

### 5. Test ausführen

```bash
python -m spacemolt run "Überprüfe meinen Status und meine Cargos"
```

---

## Detaillierte Konfiguration

### SpaceMolt API Credentials

**SpaceMolt** ist ein Space-Mining MMO. Um auf das Spiel zuzugreifen, benötigst du API-Credentials vom Spielserver.

#### Wo bekommt man SpaceMolt API Credentials?

1. **Besuche spacemolt.com**
   - Website: https://game.spacemolt.com
   - Registriere ein neues Konto oder melde dich an

2. **Generiere API-Keys**
   - Nach dem Login: Account Settings → Developer/API
   - Klicke auf "Generate API Key"
   - Kopiere deinen **API Key** (Achtung: wird nur einmalig angezeigt!)

3. **Speichere die Credentials**
   - Diese brauchst du NICHT direkt in `config.yaml`
   - Der Commander speichert sie sicher in `~/.spacemolt_commander/sessions/{session_name}/`

#### Erstes Login

Beim ersten Ausführen des Commanders:
- Der Commander fragt nach deinem SpaceMolt API-Key
- Beantworte die Frage mit deinem **API Key**
- Die Credentials werden verschlüsselt lokal gespeichert
- Alternativ nutze die `--force-credentials` Flag zum Überschreiben:

```bash
python -m spacemolt run "Meine Mission" --force-credentials
```

---

### LLM Backend Konfiguration

Der Commander nutzt **zwei LLM-Modelle**:

1. **Cloud Model** (komplex, strategisch)
   - Anthropic Claude, OpenAI GPT-4, oder Abacus.AI LLMs
   - Für strategische Planung, Codeanalyse, komplexe Entscheidungen

2. **Local Model** (schnell, einfach)
   - Ollama (lokal auf deinem Rechner)
   - Für einfache API-Calls, Status-Checks, schnelle Reaktionen

#### Option A: Cloud Models verwenden

**Anthropic Claude** (empfohlen)

1. Besuche https://console.anthropic.com/
2. Registriere dich oder melde dich an
3. Klicke auf "API Keys" in der Sidebar
4. Generiere einen neuen **API Key**
5. Setze die Umgebungsvariable:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**OpenAI GPT-4**

1. Besuche https://platform.openai.com/account/api-keys
2. Generiere einen neuen API Key
3. Setze die Umgebungsvariable:

```bash
export OPENAI_API_KEY="sk-..."
```

**Groq (schnelle offene Modelle)**

1. Besuche https://console.groq.com/keys
2. Generiere einen API Key
3. Setze die Umgebungsvariable:

```bash
export GROQ_API_KEY="gsk_..."
```

#### Option B: Abacus.AI Integration

Falls du bereits ein Abacus.AI-Abo hast:

1. Hole deinen API-Key aus https://abacus.ai/app/account
2. Setze die Umgebungsvariable:

```bash
export ABACUS_API_KEY="abacusai_..."
```

3. Nutze ein Abacus.AI-Modell in `config.yaml`:

```yaml
cloud_model: "abacus/gpt-4-turbo"  # oder andere verfügbare Modelle
```

#### Option C: Lokale Ollama-Modelle (kostenlos & privat)

Falls du keine Cloud-Keys haben möchtest oder nur local arbeiten willst:

1. **Installiere Ollama**
   - Download: https://ollama.ai
   - Folge der Installationsanleitung für dein OS

2. **Lade ein Modell herunter**

```bash
# Schnell & leicht (8B parameter)
ollama pull qwen3:8b

# Oder andere Optionen:
ollama pull llama3.1:8b
ollama pull mistral:7b
ollama pull deepseek-r1:7b
```

3. **Starte den Ollama Server**

```bash
ollama serve
```

Der Server läuft auf `http://localhost:11434` (Standard).

4. **Konfiguriere in `config.yaml`**

```yaml
local_model: "ollama/qwen3:8b"
backend: "local"  # Nur lokale Modelle verwenden
```

---

### Lokale Ollama-Modelle

**Empfohlene Modelle nach Anwendungsfall:**

| Modell | Parameter | Best For | Performance | Context |
|--------|-----------|----------|-------------|---------|
| **qwen3:8b** | 8B | Balance | Sehr schnell | 32K |
| **llama3.1:8b** | 8B | Allgemein | Schnell | 128K |
| **deepseek-r1:7b** | 7B | Reasoning | Moderat | 128K |
| **mistral:7b** | 7B | Schnelligkeit | Sehr schnell | 32K |
| **neural-chat:7b** | 7B | Chat | Schnell | 32K |

**Größere Modelle (erfordern mehr RAM):**

```bash
ollama pull qwen3:32b    # 19GB RAM
ollama pull llama3.1:70b # 40GB RAM
```

---

## Konfigurationsdatei `config.yaml`

### Vollständiges Beispiel

```yaml
# ============================================================================
# SpaceMolt Commander — Production Configuration
# ============================================================================

# --- LLM Models ---
# cloud_model: Für komplexe Strategien und Codeanalyse
# local_model: Für einfache API-Calls und schnelle Reaktionen
cloud_model: "anthropic/claude-sonnet-4-20250514"
local_model: "ollama/qwen3:8b"

# --- SpaceMolt API ---
# Base URL des Spielservers
api_url: "https://game.spacemolt.com/api/v2"

# --- Session Management ---
# Eindeutige Kennung für Spielzustände
# Der Commander speichert Credentials und State in ~/.spacemolt_commander/sessions/{session_name}/
session_name: "default"

# Andere Sessions: "farming", "trading", "exploration"
# Jede Session hat eigene Credentials und Spielzustände

# --- Mission ---
# Die Anweisung für den autonomen Agenten
# Der Agent verfolgt diese Mission kontinuierlich
mission: "Erkunde die Galaxie, baue Erz ab, handle gewinnbringend und werde stärker."

# --- Behavior & Debugging ---
debug: false
# true  = detaillierte Logs (für Debugging)
# false = nur wichtige Nachrichten

force_credentials: false
# false = gespeicherte Credentials verwenden
# true  = beim nächsten Start nach API-Key fragen (zum Wechsel des Accounts)

# --- LLM Backend ---
# auto  = intelligentes Routing (einfache Aufgaben → local, komplexe → cloud)
# local = nur Ollama verwenden (schneller, kostenlos, weniger Fähigkeiten)
# cloud = nur Cloud-Modelle verwenden (besser für Planung, kostet API-Credits)
backend: "auto"

# ============================================================================
# Umgebungsvariablen (in deiner Shell setzen, NICHT hier)
# ============================================================================
# export ANTHROPIC_API_KEY="sk-ant-..."
# export OPENAI_API_KEY="sk-..."
# export GROQ_API_KEY="gsk_..."
# export ABACUS_API_KEY="..."

# Dauerhaft setzen (für macOS/Linux):
# Füge folgende Zeilen am Ende von ~/.zshrc oder ~/.bashrc ein:
# export ANTHROPIC_API_KEY="sk-ant-..."
```

### Detaillierte Feldförklärung

#### `cloud_model`

**Beschreibung:** Das Cloud-Modell für komplexe Aufgaben

**Mögliche Werte:**

```yaml
# Anthropic (empfohlen)
cloud_model: "anthropic/claude-sonnet-4-20250514"
cloud_model: "anthropic/claude-3-haiku-20240307"

# OpenAI
cloud_model: "openai/gpt-4o"
cloud_model: "openai/gpt-4o-mini"

# Groq (schneller & kostenlos)
cloud_model: "groq/mixtral-8x7b-32768"

# Abacus.AI
cloud_model: "abacus/gpt-4-turbo"
```

**Erfordert:** Entsprechende Umgebungsvariable (`ANTHROPIC_API_KEY`, etc.)

#### `local_model`

**Beschreibung:** Das lokale Modell (via Ollama)

**Mögliche Werte:**

```yaml
local_model: "ollama/qwen3:8b"
local_model: "ollama/llama3.1:8b"
local_model: "ollama/deepseek-r1:7b"
local_model: "ollama/mistral:7b"
```

**Erfordert:** Ollama installiert & `ollama serve` läuft auf `localhost:11434`

#### `api_url`

**Beschreibung:** SpaceMolt API Endpoint

**Standard:** `https://game.spacemolt.com/api/v2`

**Ändern nur wenn:** Du einen custom oder lokalen SpaceMolt Server nutzt

#### `session_name`

**Beschreibung:** Eindeutige ID für diesen Spieler/Charakter

**Bestimmt:**
- Wo Credentials gespeichert werden: `~/.spacemolt_commander/sessions/{session_name}/`
- Wo der Spielzustand (TODO, Handoff) gespeichert wird
- Welche Credentials beim Start geladen werden

**Beispiele:**

```yaml
session_name: "default"        # Dein Hauptcharakter
session_name: "farm-bot"       # Ein Bot für Mining-Farming
session_name: "trader-bot"     # Ein Bot für Handel
```

#### `mission`

**Beschreibung:** Langfristige Anweisung für den Agent

**Wird verwendet für:** High-Level Planung und Zielsetzung

**Beispiele:**

```yaml
# Exploitation (Farming)
mission: "Maximiere mein Vermögen durch kontinuierliches Ore-Mining und Verkauf"

# Trading
mission: "Finde profitable Handelsmöglichkeiten zwischen Raumstationen"

# Exploration
mission: "Erkunde jeden unbekannten Sektor und kartografiere den Raum"

# Hybrid
mission: "Balance zwischen Ore-Mining, Trading und Raumfahrt-Verbesserungen"
```

#### `debug`

**Beschreibung:** Aktiviert ausführliches Logging

**Werte:**
- `false` (Standard): Nur wichtige Meldungen
- `true`: Vollständiges Logging (CLI und `~/.spacemolt_commander/logs/`)

**Verwende zum Debugging:** `--debug` Flag oder `debug: true` in config.yaml

#### `force_credentials`

**Beschreibung:** Beim nächsten Start erneut nach API-Key fragen

**Werte:**
- `false` (Standard): Gespeicherte Credentials verwenden
- `true`: Credentials erneut eingeben (z.B. für Account-Wechsel)

**Verwendet:** `python -m spacemolt run "Mission" --force-credentials`

#### `backend`

**Beschreibung:** LLM Backend-Auswahl-Strategie

**Werte:**

| Value | Verhalten | Beste für |
|-------|-----------|-----------|
| `auto` | Intelligentes Routing (einfach→local, komplex→cloud) | Balanced Performance & Kosten |
| `local` | Nur Ollama (schnell, kostenlos, weniger Fähigkeiten) | Budget-Betrieb, Privatsphäre |
| `cloud` | Nur Cloud-Modelle (beste Fähigkeiten, kostet Credits) | Maximale Intelligenz |

---

## LLM-Modelle Empfehlungen

### Für verschiedene Spielziele

#### 🏆 Best Overall: Balance

```yaml
backend: "auto"
cloud_model: "anthropic/claude-sonnet-4-20250514"
local_model: "ollama/qwen3:8b"
```

**Warum:** Claude-Sonnet ist sehr fähig für Planung, Qwen3:8b ist schnell für einfache Calls.

#### 💰 Budget-Option: Nur Lokal

```yaml
backend: "local"
local_model: "ollama/qwen3:8b"
```

**Warum:** Komplett kostenlos, schnell genug für die meisten Gameplay-Aufgaben.

#### 🚀 High-Performance: Maximum Intelligence

```yaml
backend: "cloud"
cloud_model: "anthropic/claude-sonnet-4-20250514"
```

**Warum:** Beste Strategische Planung und Entscheidungen (höhere API-Kosten).

#### 🔬 Reasoning-Fokus: DeepSeek

```yaml
backend: "auto"
cloud_model: "openai/gpt-4o"
local_model: "ollama/deepseek-r1:7b"
```

**Warum:** DeepSeek-R1 ist gut im Chain-of-Thought Reasoning (Kostenlos lokal).

---

## Umgebungsvariablen einrichten

### Temporär (nur aktuelle Shell-Session)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python -m spacemolt run "Meine Mission"
```

### Dauerhaft (macOS/Linux)

**Öffne deine Shell-Konfigdatei:**

```bash
# Für bash:
nano ~/.bashrc

# Für zsh (default macOS):
nano ~/.zshrc
```

**Füge am Ende ein:**

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GROQ_API_KEY="gsk_..."
export ABACUS_API_KEY="..."
```

**Speichern:** `Ctrl+O`, `Enter`, `Ctrl+X`

**Aktivieren:**

```bash
source ~/.zshrc  # oder ~/.bashrc
```

**Verifizieren:**

```bash
echo $ANTHROPIC_API_KEY
```

### Windows (PowerShell)

```powershell
# Temporär
$env:ANTHROPIC_API_KEY="sk-ant-..."

# Dauerhaft
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-...", "User")
```

---

## Troubleshooting

### ❌ "API Key not found" / "Invalid credentials"

**Problem:** Commander kann SpaceMolt API nicht authentifizieren

**Lösungen:**

1. **API-Key überprüfen**
   ```bash
   # Hast du einen gültigen Key von spacemolt.com?
   python -m spacemolt run "Check" --force-credentials
   ```

2. **Session zurücksetzen**
   ```bash
   rm -rf ~/.spacemolt_commander/sessions/default
   python -m spacemolt run "Test" --force-credentials
   ```

3. **URL überprüfen**
   ```yaml
   api_url: "https://game.spacemolt.com/api/v2"
   # Korrekt? (Nicht localhost o.ä.)
   ```

---

### ❌ "Ollama model not found" / Local model fails

**Problem:** Lokales Modell kann nicht geladen werden

**Lösungen:**

1. **Ollama läuft nicht**
   ```bash
   # Terminal öffnen und starten:
   ollama serve
   ```

2. **Modell nicht heruntergeladen**
   ```bash
   # Verfügbare Modelle auflisten:
   ollama list
   
   # Modell herunterladen:
   ollama pull qwen3:8b
   ```

3. **Falscher Modellname in config.yaml**
   ```yaml
   # Verwende exakten Namen:
   local_model: "ollama/qwen3:8b"  # RICHTIG
   local_model: "ollama/qwen"      # FALSCH
   ```

---

### ❌ "Cloud API connection failed"

**Problem:** Anthropic/OpenAI/Groq API antwortet nicht

**Lösungen:**

1. **Umgebungsvariable nicht gesetzt**
   ```bash
   # Überprüfen:
   echo $ANTHROPIC_API_KEY
   
   # Sollte einen Key ausgeben, nicht leer
   ```

2. **API-Key abgelaufen oder ungültig**
   - Besuche https://console.anthropic.com/
   - Generiere neuen Key
   - Setze Umgebungsvariable neu

3. **Rate Limit oder Quota überschritten**
   - Warte 60 Sekunden
   - Überprüfe deinen Account-Status in der Web-Konsole

4. **Internet-Verbindung**
   ```bash
   # Test:
   curl https://api.anthropic.com
   ```

---

### ❌ "GPU out of memory" (nur bei großen Ollama-Modellen)

**Problem:** Lokales Modell zu groß für deine Hardware

**Lösungen:**

1. **Kleineres Modell verwenden**
   ```yaml
   local_model: "ollama/qwen3:8b"  # Statt 32b
   ```

2. **RAM reduzieren**
   ```bash
   # Ollama config anpassen:
   export OLLAMA_NUM_GPU=1
   ollama serve
   ```

3. **Nur Cloud verwenden**
   ```yaml
   backend: "cloud"
   ```

---

### ❌ "Connection timed out" bei SpaceMolt API

**Problem:** Game Server antwortet nicht

**Lösungen:**

1. **Server ist down oder zu langsam**
   - Besuche https://game.spacemolt.com
   - Funktioniert die Website?

2. **Firewall blockiert**
   ```bash
   # Teste Verbindung:
   curl https://game.spacemolt.com/api/v2/
   ```

3. **Proxy erforderlich**
   - Falls du hinter einem Proxy sitzt, konfiguriere in `.env`:
   ```bash
   export HTTP_PROXY="http://proxy.example.com:8080"
   ```

---

## Sicherheit

### 🔐 Best Practices

**1. API-Keys sicher speichern**

❌ NICHT in Code-Repos committen:
```bash
# Never do this:
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> config.yaml
```

✅ Verwende Umgebungsvariablen:
```bash
# Besser:
export ANTHROPIC_API_KEY="sk-ant-..."
```

✅ Nutze `.env`-Datei (gitignored):
```bash
# .env (nie committen!)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

Dann laden in Python:
```python
from dotenv import load_dotenv
load_dotenv()
```

**2. Credentials rotieren**

Regelmäßig neue API-Keys generieren:
```bash
# Alle 3 Monate:
1. Neuen Key in Anbieter-Konsole generieren
2. Umgebungsvariable updaten
3. Alten Key deaktivieren
```

**3. Session-Datensicherung**

Der Commander speichert Session-Credentials verschlüsselt:
```bash
# Backup erstellen:
tar -czf spacemolt_backup.tar.gz ~/.spacemolt_commander/

# Backup wiederherstellen:
tar -xzf spacemolt_backup.tar.gz -C ~/
```

**4. API-Key Einschränkungen**

Wenn dein API-Provider erlaubt, beschränke die Keys:
- **Anthropic:** IP-Whitelist (falls verfügbar)
- **OpenAI:** Spending limits setzen
- **Groq:** Rate limits

---

### 🛡️ Credentials in Shared Systems

Wenn du den Code mit anderen teilst:

```bash
# 1. Config-Datei zu .gitignore hinzufügen:
echo "config.yaml" >> .gitignore
echo ".env" >> .gitignore

# 2. Nur example-Datei committen:
git add config.example.yaml
git commit -m "Add config example (template only)"

# 3. Credentials lokal speichern:
cp config.example.yaml config.yaml
# ...API-Keys eintragen...

# 4. Verifizieren, dass nichts geleakt wird:
git status  # config.yaml sollte NICHT in der Liste sein
```

---

## Häufig gestellte Fragen (FAQ)

### F: Kostet die Nutzung des Commanders etwas?

**A:** 
- **SpaceMolt:** Kostenlos zum Spielen
- **Anthropic/OpenAI/Groq APIs:** Bezahlt nach Nutzung
- **Abacus.AI:** Je nach Abo
- **Ollama lokal:** Komplett kostenlos

### F: Wie viel kostet ein typischer Tag Betrieb?

**A:** Hängt von Nutzung ab:
- **Nur lokal (Ollama):** $0
- **Auto-Routing mit Claude:** $0.10–$1 pro Tag (abhängig von Komplexität)
- **Nur Cloud (Claude):** $1–$5 pro Tag

### F: Kann ich mehrere Sessions gleichzeitig laufen lassen?

**A:** Ja! Nutze unterschiedliche `session_name`:

```bash
# Terminal 1: Farming-Bot
python -m spacemolt run "Mine ore" --session farm-bot

# Terminal 2: Trading-Bot
python -m spacemolt run "Find profits" --session trader-bot
```

Jede Session hat eigene Credentials und Spielzustände.

### F: Was ist der Unterschied zwischen `--debug` und `debug: true`?

**A:**
- `--debug` Flag: Nur aktuelle CLI-Session
- `debug: true` in config.yaml: Immer aktiviert
- Logfiles unter: `~/.spacemolt_commander/logs/`

### F: Kann ich den Backend während des Betriebs umschalten?

**A:** Ja, aber nur zwischen Runs:

```bash
# Backend in config.yaml ändern:
backend: "local"  # Statt "auto"

# Dann neu starten:
python -m spacemolt run "Mission"
```

Live-Umschalten während eines Runs ist nicht möglich.

---

## Nächste Schritte

1. **Setup-Script ausführen** (optional):
   ```bash
   python setup_config.py
   ```

2. **Erste Mission testen**:
   ```bash
   python -m spacemolt run "Überprüfe meinen Spielzustand"
   ```

3. **Session-Status prüfen**:
   ```bash
   python -m spacemolt status
   ```

4. **Service-Mode starten** (kontinuierlicher Betrieb):
   ```bash
   python -m spacemolt service --mission "Meine Mission"
   ```

---

## Support & Ressourcen

- **SpaceMolt Official:** https://game.spacemolt.com
- **Commander GitHub:** https://github.com/rddaz2013/spacemolt-commander-python
- **Anthropic Docs:** https://docs.anthropic.com
- **Ollama Docs:** https://ollama.ai/library
- **litellm Docs:** https://docs.litellm.ai
