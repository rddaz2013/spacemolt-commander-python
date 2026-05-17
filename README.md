# SpaceMolt Commander (Python)

Python implementation of SpaceMolt Commander with hybrid LLM architecture and token optimization.

## Overview

SpaceMolt Commander is a command-line tool that interfaces with the [Spacemolt](https://game.spacemolt.com) game API and uses the Abacus RouteLLM API for intelligent command assistance.

### Key Features

- **Game API v2 Integration** — Communicates with `https://game.spacemolt.com/api/v2/`
- **Hybrid LLM Architecture** — Uses Abacus RouteLLM for intelligent responses with token optimization
- **Session Management** — Per-session configuration and logging under `~/.spacemolt/sessions/`
- **Detailed Logging** — Timestamps and function names in every log entry

## Quick Start

```bash
# Clone the repository
git clone https://github.com/rddaz2013/spacemolt-commander-python.git
cd spacemolt-commander-python

# Install dependencies
pip3 install -r requirements.txt

# Run setup
python3 -m spacemolt_commander --setup

# Start the commander
python3 -m spacemolt_commander
```

## Documentation

See [Setup_Install.md](Setup_Install.md) for detailed installation instructions, usage examples, and troubleshooting.

## Configuration

Copy the example configuration or run the interactive setup:

```bash
python3 -m spacemolt_commander --setup
```

Configuration is stored at `~/.spacemolt/sessions/default/config.yaml`.
See [config.example.yaml](config.example.yaml) for all available options.

## License

[MIT](LICENSE)
