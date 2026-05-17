# SpaceMolt Commander — Setup & Installation Guide (Linux)

This guide covers installing and configuring **SpaceMolt Commander** on Linux systems.

---

### System Requirements

| Requirement       | Minimum Version |
|-------------------|-----------------|
| Operating System  | Linux (Ubuntu 20.04+, Debian 11+, Fedora 36+, Arch) |
| Python            | 3.9 or higher   |
| pip               | 21.0 or higher  |
| Network           | Internet access for API calls |

Verify your Python and pip versions:

```bash
python3 --version
pip3 --version
```

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/rddaz2013/spacemolt-commander-python.git
cd spacemolt-commander-python
```

---

### Step 2 — Install Dependencies

Install the required Python packages with pip:

```bash
pip3 install -r requirements.txt
```

This installs:

- **PyYAML** — YAML configuration parsing
- **requests** — HTTP client for Game API and LLM API calls

---

### Step 3 — Run the Configuration Setup

Run the interactive setup to create your default session:

```bash
python3 -m spacemolt_commander --setup
```

The setup will prompt you for:

1. **Abacus RouteLLM API Key** — Get yours at [https://apps.abacus.ai/](https://apps.abacus.ai/)
2. **Player Name** — Your in-game player name

The setup creates the following directory structure:

```
~/.spacemolt/
└── sessions/
    └── default/
        ├── config.yaml      # Your session configuration
        └── session.log      # Log file (created on first run)
```

#### Configuration Details

The generated `config.yaml` includes:

- **LLM settings**: Abacus RouteLLM API key, base URL, model, token limits
- **Game API**: Default endpoint `https://game.spacemolt.com/api/v2/`
- **Player**: Your configured player name
- **Logging**: Detailed logging enabled with timestamps and function names

---

### Step 4 — Run SpaceMolt Commander

```bash
python3 -m spacemolt_commander
```

You should see:

```
SpaceMolt Commander ready — Player: YourPlayerName
Game API: https://game.spacemolt.com/api/v2/
Type 'help' for available commands, 'quit' to exit.

[SpaceMolt]>
```

---

### Basic Usage Examples

#### Check Player Status

```
[SpaceMolt]> status
```

#### View Game State

```
[SpaceMolt]> state
```

#### Ask the LLM a Question

```
[SpaceMolt]> ask What is the best strategy for resource gathering?
```

#### Send a Custom Command

```
[SpaceMolt]> scout sector-7
```

#### Exit the Commander

```
[SpaceMolt]> quit
```

---

### Configuration File Reference

You can also manually edit the configuration. Copy the example:

```bash
mkdir -p ~/.spacemolt/sessions/default
cp config.example.yaml ~/.spacemolt/sessions/default/config.yaml
```

Then edit `~/.spacemolt/sessions/default/config.yaml` with your API key and player name.

---

### Logging

SpaceMolt Commander uses detailed logging by default:

- **Log file**: `~/.spacemolt/sessions/default/session.log`
- **Format**: `2026-05-17 14:30:00 - spacemolt_commander - my_function - INFO - Message`
- **Includes**: Timestamps, module names, function names, log levels

To adjust the log level, edit the `logging.level` field in your `config.yaml` (options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).

---

### Troubleshooting

#### "Config not found" Error

```
[ERROR] Config not found at ~/.spacemolt/sessions/default/config.yaml
```

**Solution**: Run the setup first:

```bash
python3 -m spacemolt_commander --setup
```

#### ModuleNotFoundError: No module named 'yaml'

```
ModuleNotFoundError: No module named 'yaml'
```

**Solution**: Install the dependencies:

```bash
pip3 install -r requirements.txt
```

#### ModuleNotFoundError: No module named 'spacemolt_commander'

**Solution**: Make sure you are running from the project root directory:

```bash
cd spacemolt-commander-python
python3 -m spacemolt_commander
```

#### Permission Denied When Writing Config

```
PermissionError: [Errno 13] Permission denied
```

**Solution**: Check permissions on your home directory:

```bash
ls -la ~/.spacemolt/
chmod -R u+rw ~/.spacemolt/
```

#### Connection Timeout to Game API

```
requests.exceptions.ConnectionError
```

**Solution**:
1. Verify your internet connection
2. Check if the API endpoint is reachable: `curl -I https://game.spacemolt.com/api/v2/`
3. Increase the `timeout` value in your `config.yaml`

#### Invalid or Expired API Key

**Solution**:
1. Verify your Abacus RouteLLM API key at [https://apps.abacus.ai/](https://apps.abacus.ai/)
2. Re-run setup to update: `python3 -m spacemolt_commander --setup`

#### Checking Logs for Errors

Review the session log for detailed error information:

```bash
tail -50 ~/.spacemolt/sessions/default/session.log
```

---

### Project Structure

```
spacemolt-commander-python/
├── config.example.yaml                  # Example configuration file
├── requirements.txt                     # Python dependencies
├── Setup_Install.md                     # This file
├── README.md                            # Project overview
├── LICENSE                              # MIT License
└── spacemolt_commander/
    ├── __init__.py                      # Package init
    ├── __main__.py                      # Main entry point
    ├── setup_config.py                  # Interactive setup
    ├── logger.py                        # Logging configuration
    ├── api_client.py                    # Game API client (v2)
    └── llm_client.py                    # Abacus RouteLLM client
```
