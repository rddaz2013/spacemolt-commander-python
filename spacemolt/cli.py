"""CLI entry point for SpaceMolt Commander.

Supports two modes:
  1. Interactive CLI (default) — single mission run
  2. Service mode (--service) — continuous autonomous operation
"""

from __future__ import annotations

import asyncio
import sys

import click

from spacemolt import __version__


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="spacemolt-commander")
@click.pass_context
def main(ctx: click.Context) -> None:
    """🚀 SpaceMolt Commander — Autonomous AI agent for the SpaceMolt MMO."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.argument("mission")
@click.option("--model", default=None, help="Cloud LLM model (e.g. anthropic/claude-sonnet-4-20250514)")
@click.option("--local-model", default=None, help="Local LLM model (e.g. ollama/qwen3:8b)")
@click.option("--session", "session_name", default="default", help="Session name for state persistence")
@click.option("--url", default=None, help="SpaceMolt API base URL")
@click.option("--ollama-url", default=None, help="Ollama base URL (e.g. http://192.168.1.100:11434)")
@click.option("--cloud-url", default=None, help="Cloud LLM base URL (e.g. https://routellm.abacus.ai/v1)")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--force-credentials", is_flag=True, help="Allow overwriting stored credentials")
@click.option("--backend", type=click.Choice(["auto", "local", "cloud"]), default="auto",
              help="Force a specific LLM backend")
def run(
    mission: str,
    model: str | None,
    local_model: str | None,
    session_name: str,
    url: str | None,
    ollama_url: str | None,
    cloud_url: str | None,
    debug: bool,
    force_credentials: bool,
    backend: str,
) -> None:
    """Run the commander with a MISSION (e.g. 'mine ore and get rich')."""
    asyncio.run(_run_async(
        mission=mission,
        model=model,
        local_model=local_model,
        session_name=session_name,
        url=url,
        ollama_url=ollama_url,
        cloud_url=cloud_url,
        debug=debug,
        force_credentials=force_credentials,
        backend=backend,
    ))


@main.command()
@click.option("--model", default=None, help="Cloud LLM model")
@click.option("--local-model", default=None, help="Local LLM model")
@click.option("--session", "session_name", default="default", help="Session name")
@click.option("--url", default=None, help="SpaceMolt API base URL")
@click.option("--ollama-url", default=None, help="Ollama base URL")
@click.option("--cloud-url", default=None, help="Cloud LLM base URL")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--mission", default="Explore, mine, trade, and grow stronger.", help="Default mission")
def service(
    model: str | None,
    local_model: str | None,
    session_name: str,
    url: str | None,
    ollama_url: str | None,
    cloud_url: str | None,
    debug: bool,
    mission: str,
) -> None:
    """Run in continuous service mode (autonomous operation)."""
    click.echo("🔄 Starting in service mode…")
    asyncio.run(_run_async(
        mission=mission,
        model=model,
        local_model=local_model,
        session_name=session_name,
        url=url,
        ollama_url=ollama_url,
        cloud_url=cloud_url,
        debug=debug,
        force_credentials=False,
        backend="auto",
    ))


@main.command()
@click.option("--session", "session_name", default="default", help="Session name")
def status(session_name: str) -> None:
    """Show the current session status."""
    from spacemolt.session import SessionStore
    store = SessionStore(session_name)
    creds = store.load_credentials()
    todo = store.read_todo()
    handoff = store.load_handoff()

    click.echo(f"📂 Session: {session_name}")
    if creds:
        click.echo(f"👤 Player: {creds.username} ({creds.empire})")
    else:
        click.echo("👤 No credentials stored")

    if todo:
        click.echo(f"\n📋 TODO:\n{todo}")
    if handoff:
        click.echo(f"\n📝 Last handoff:\n{handoff}")


# ---------------------------------------------------------------------------
# Async runner
# ---------------------------------------------------------------------------

async def _run_async(
    *,
    mission: str,
    model: str | None,
    local_model: str | None,
    session_name: str,
    url: str | None,
    ollama_url: str | None = None,
    cloud_url: str | None = None,
    debug: bool,
    force_credentials: bool,
    backend: str,
) -> None:
    from spacemolt.api import SpaceMoltAPI, DEFAULT_BASE_URL
    from spacemolt.commander import Commander
    from spacemolt.llm_router import LLMRouter, DEFAULT_CLOUD_MODEL, DEFAULT_LOCAL_MODEL
    from spacemolt.models import LLMBackend

    # Build router
    force_be = None
    if backend == "local":
        force_be = LLMBackend.LOCAL
    elif backend == "cloud":
        force_be = LLMBackend.CLOUD

    router = LLMRouter(
        cloud_model=model or DEFAULT_CLOUD_MODEL,
        local_model=local_model or DEFAULT_LOCAL_MODEL,
        force_backend=force_be,
        ollama_base_url=ollama_url,
        cloud_base_url=cloud_url,
    )

    # Build API client
    api = SpaceMoltAPI(base_url=url or DEFAULT_BASE_URL, debug=debug)

    # Build and start commander
    commander = Commander(
        mission=mission,
        session_name=session_name,
        router=router,
        api=api,
        force_credentials=force_credentials,
        debug=debug,
    )
    await commander.start()


if __name__ == "__main__":
    main()
