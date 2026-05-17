#!/usr/bin/env python3
"""
Interactive setup script for SpaceMolt Commander configuration.

Guides users through:
1. SpaceMolt API credentials
2. LLM backend selection
3. Cloud API key setup
4. Ollama model configuration
5. Session setup

Creates config.yaml automatically.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional, Tuple


# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str) -> None:
    """Print a colored header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^70}{Colors.RESET}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.RESET}\n")


def print_section(text: str) -> None:
    """Print a section header."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}▶ {text}{Colors.RESET}")
    print(f"{Colors.CYAN}{'-' * (len(text) + 2)}{Colors.RESET}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def prompt(question: str, default: Optional[str] = None, required: bool = True) -> str:
    """
    Prompt user for input.
    
    Args:
        question: The question to ask
        default: Default value if user presses Enter
        required: If True, reject empty input
    
    Returns:
        User's response
    """
    while True:
        default_str = f" [{default}]" if default else ""
        full_question = f"{Colors.BOLD}{question}{default_str}:{Colors.RESET} "
        response = input(full_question).strip()
        
        if not response and default:
            return default
        
        if not response and required:
            print_error("This field is required. Please enter a value.")
            continue
        
        if not response and not required:
            return ""
        
        return response


def prompt_choice(question: str, options: list[str]) -> str:
    """
    Prompt user to choose from a list.
    
    Args:
        question: The question to ask
        options: List of options
    
    Returns:
        Selected option
    """
    print(f"\n{Colors.BOLD}{question}{Colors.RESET}")
    for i, option in enumerate(options, 1):
        print(f"  {Colors.CYAN}{i}){Colors.RESET} {option}")
    
    while True:
        choice = input(f"{Colors.BOLD}Select (1-{len(options)}):{Colors.RESET} ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        print_error(f"Please enter a number between 1 and {len(options)}")


def check_ollama_running() -> bool:
    """Check if Ollama server is running."""
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434"],
            capture_output=True,
            timeout=2
        )
        return result.returncode == 0
    except Exception:
        return False


def get_ollama_models() -> list[str]:
    """Get list of installed Ollama models."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            models = []
            for line in lines:
                if line.strip():
                    model_name = line.split()[0]
                    models.append(f"ollama/{model_name}")
            return models
    except Exception:
        pass
    return []


def setup_spacemolt_credentials() -> dict:
    """Setup SpaceMolt API credentials."""
    print_section("SpaceMolt API Credentials")
    
    print_info(
        "SpaceMolt is a space mining MMO. Get your API credentials from:"
    )
    print(f"  {Colors.BOLD}https://game.spacemolt.com{Colors.RESET}")
    print()
    print_info("After login: Account Settings → Developer/API → Generate API Key")
    print_info("⚠  Your API key will only be shown once! Copy it carefully.")
    
    api_url = prompt(
        "SpaceMolt API URL",
        default="https://game.spacemolt.com/api/v2",
        required=False
    )
    
    session_name = prompt(
        "Session name (for storing credentials)",
        default="default",
        required=False
    )
    
    return {
        "api_url": api_url or "https://game.spacemolt.com/api/v2",
        "session_name": session_name or "default"
    }


def setup_llm_backend() -> Tuple[str, str, str]:
    """Setup LLM backend selection."""
    print_section("LLM Backend Selection")
    
    print_info("The Commander uses TWO LLMs:")
    print("  • Cloud Model: For complex tasks (strategy, planning, code)")
    print("  • Local Model: For simple tasks (status checks, API calls)")
    print()
    
    backend_options = [
        "Auto (intelligent routing)",
        "Cloud only (best quality, costs money)",
        "Local only (free & private)"
    ]
    
    backend_choice = prompt_choice(
        "Choose backend strategy",
        backend_options
    )
    
    backend = {
        "Auto (intelligent routing)": "auto",
        "Cloud only (best quality, costs money)": "cloud",
        "Local only (free & private)": "local"
    }[backend_choice]
    
    return backend


def setup_cloud_model() -> str:
    """Setup cloud LLM model."""
    print_section("Cloud LLM Model")
    
    print_info("Choose your cloud LLM provider:")
    
    providers = [
        "Anthropic Claude (recommended, best quality)",
        "OpenAI GPT-4",
        "Groq (free, fast)",
        "Abacus.AI"
    ]
    
    provider = prompt_choice("Select cloud provider", providers)
    
    if "Anthropic" in provider:
        print_info("Get API key: https://console.anthropic.com/")
        model = prompt(
            "Claude model",
            default="anthropic/claude-sonnet-4-20250514",
            required=False
        )
        env_var = ("ANTHROPIC_API_KEY", "sk-ant-...")
    
    elif "OpenAI" in provider:
        print_info("Get API key: https://platform.openai.com/api-keys")
        model = prompt(
            "OpenAI model",
            default="openai/gpt-4o",
            required=False
        )
        env_var = ("OPENAI_API_KEY", "sk-...")
    
    elif "Groq" in provider:
        print_info("Get API key: https://console.groq.com/keys")
        model = prompt(
            "Groq model",
            default="groq/mixtral-8x7b-32768",
            required=False
        )
        env_var = ("GROQ_API_KEY", "gsk_...")
    
    else:  # Abacus.AI
        print_info("Get API key: https://abacus.ai/app/account")
        model = prompt(
            "Abacus.AI model",
            default="abacus/gpt-4-turbo",
            required=False
        )
        env_var = ("ABACUS_API_KEY", "...")
    
    print_warning(f"Set environment variable: {env_var[0]}=\"{env_var[1]}\"")
    
    return model or "anthropic/claude-sonnet-4-20250514"


def setup_local_model() -> str:
    """Setup local Ollama model."""
    print_section("Local LLM Model (Ollama)")
    
    ollama_installed = subprocess.run(
        ["which", "ollama"],
        capture_output=True
    ).returncode == 0
    
    if not ollama_installed:
        print_error("Ollama is not installed!")
        print_info("Install from: https://ollama.ai")
        install = prompt(
            "Would you like to continue without local model setup?",
            default="y",
            required=False
        ).lower()
        return "ollama/qwen3:8b"
    
    if not check_ollama_running():
        print_warning("Ollama server is not running")
        print_info("Start with: ollama serve")
        return "ollama/qwen3:8b"
    
    installed_models = get_ollama_models()
    
    if installed_models:
        print_success(f"Found {len(installed_models)} installed model(s)")
        installed_models.append("Download a different model...")
        model = prompt_choice("Select local model", installed_models)
        
        if "Download" in model:
            model_name = prompt(
                "Model to download (e.g. qwen3:8b, llama3.1:8b, mistral:7b)",
                required=False
            )
            if model_name:
                print_info(f"Run: ollama pull {model_name}")
                return f"ollama/{model_name}"
    else:
        print_warning("No Ollama models installed")
        print_info("Download a model: ollama pull qwen3:8b")
    
    model = prompt(
        "Local model to use",
        default="ollama/qwen3:8b",
        required=False
    )
    
    return model or "ollama/qwen3:8b"


def setup_mission() -> str:
    """Setup mission description."""
    print_section("Mission Description")
    
    print_info("Define your mission for the autonomous agent.")
    print_info("Examples:")
    print("  • 'Mine ore and maximize profit'")
    print("  • 'Explore and map unknown sectors'")
    print("  • 'Trade for profit between stations'")
    print()
    
    mission = prompt(
        "Your mission",
        default="Explore the galaxy, mine ore, trade for profit, and grow stronger.",
        required=False
    )
    
    return mission or "Explore the galaxy, mine ore, trade for profit, and grow stronger."


def generate_config(
    api_url: str,
    session_name: str,
    backend: str,
    cloud_model: str,
    local_model: str,
    mission: str
) -> str:
    """Generate config.yaml content."""
    
    return f"""# SpaceMolt Commander — Configuration
# Generated by setup_config.py

# --- LLM Models ---
cloud_model: "{cloud_model}"
local_model: "{local_model}"

# --- API ---
api_url: "{api_url}"

# --- Session ---
session_name: "{session_name}"

# --- Mission ---
mission: "{mission}"

# --- Behavior ---
debug: false
force_credentials: false

# --- LLM Backend ---
# auto  = intelligent routing (local for simple, cloud for complex)
# local = Ollama only (fast, free)
# cloud = Cloud models only (best quality, costs credits)
backend: "{backend}"

# --- Environment Variables ---
# Set these in your shell, not here:
# export ANTHROPIC_API_KEY="sk-ant-..."
# export OPENAI_API_KEY="sk-..."
# export GROQ_API_KEY="gsk_..."
# export ABACUS_API_KEY="..."
"""


def save_config(config_path: Path, content: str) -> bool:
    """Save config to file."""
    try:
        config_path.write_text(content)
        return True
    except Exception as e:
        print_error(f"Failed to save config: {e}")
        return False


def main():
    """Main setup flow."""
    print_header("SpaceMolt Commander — Interactive Setup")
    
    print_info("This wizard will help you configure the SpaceMolt Commander.")
    print_info("Press Ctrl+C at any time to cancel.")
    print()
    
    config_path = Path("config.yaml")
    if config_path.exists():
        overwrite = prompt(
            "config.yaml already exists. Overwrite?",
            default="n",
            required=False
        ).lower()
        if overwrite != "y":
            print_warning("Setup cancelled. Using existing config.")
            return
    
    try:
        # Setup sections
        spacemolt_config = setup_spacemolt_credentials()
        backend = setup_llm_backend()
        
        # Setup cloud model if needed
        if backend in ["auto", "cloud"]:
            cloud_model = setup_cloud_model()
        else:
            cloud_model = "anthropic/claude-sonnet-4-20250514"  # Unused
        
        # Setup local model if needed
        if backend in ["auto", "local"]:
            local_model = setup_local_model()
        else:
            local_model = "ollama/qwen3:8b"  # Unused
        
        # Setup mission
        mission = setup_mission()
        
        # Generate and save config
        config_content = generate_config(
            api_url=spacemolt_config["api_url"],
            session_name=spacemolt_config["session_name"],
            backend=backend,
            cloud_model=cloud_model,
            local_model=local_model,
            mission=mission
        )
        
        # Summary
        print_section("Configuration Summary")
        print(config_content)
        
        confirm = prompt(
            "Save this configuration?",
            default="y",
            required=False
        ).lower()
        
        if confirm == "y":
            if save_config(config_path, config_content):
                print_success(f"Configuration saved to {config_path}")
                
                print_section("Next Steps")
                print(f"1. Set your API key(s):")
                if backend in ["auto", "cloud"]:
                    print(f"   {Colors.BOLD}export ANTHROPIC_API_KEY=\"sk-ant-...\"{Colors.RESET}")
                
                print(f"\n2. Run the commander:")
                print(f"   {Colors.BOLD}python -m spacemolt run \"{mission}\"{Colors.RESET}")
                
                print(f"\n3. Check session status:")
                print(f"   {Colors.BOLD}python -m spacemolt status{Colors.RESET}")
                
                print(f"\n4. Start service mode (autonomous):")
                print(f"   {Colors.BOLD}python -m spacemolt service{Colors.RESET}")
                
                print_success("Setup complete! 🚀")
        else:
            print_warning("Configuration not saved.")
    
    except KeyboardInterrupt:
        print("\n")
        print_warning("Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
