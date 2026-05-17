"""Tool dispatcher — routes LLM tool calls to local handlers or the game API."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from spacemolt.api import SpaceMoltAPI
from spacemolt.code_executor import CodeExecutor, CodeExecutionError
from spacemolt.game_sequences import run_sequence
from spacemolt.models import Credentials
from spacemolt.session import SessionStore
from spacemolt.ui import log_tool_call, log_tool_result, log_error, json_to_yaml

if TYPE_CHECKING:
    from spacemolt.wiki import WikiStore

# Local tool names (including wiki, crafting, intel)
LOCAL_TOOLS = {
    "save_credentials", "update_todo", "read_todo",
    "status_log", "execute_code", "execute_sequence",
    "query_wiki", "craft_item", "check_materials",
    "get_recipes", "query_catalog", "query_intel",
    "query_trade_intel",
}


async def execute_tool(
    name: str,
    args: dict[str, Any],
    *,
    api: SpaceMoltAPI,
    session_store: SessionStore,
    code_executor: CodeExecutor,
    force_credentials: bool = False,
    wiki: "WikiStore | None" = None,
) -> str:
    """Dispatch a tool call and return the result string."""
    log_tool_call(name, args)

    try:
        if name in LOCAL_TOOLS:
            result = await _execute_local(
                name, args,
                session_store=session_store,
                api=api,
                code_executor=code_executor,
                force_credentials=force_credentials,
                wiki=wiki,
            )
        elif name == "game":
            command = args.get("command", "")
            command_args = args.get("args") or {}
            if isinstance(command_args, str):
                try:
                    command_args = json.loads(command_args)
                except json.JSONDecodeError:
                    command_args = {}
            result = await api.execute(command, command_args)
        else:
            # Fallback: treat the tool name as a direct game command
            result = await api.execute(name, args)

    except Exception as exc:
        result = f"Error: {exc}"
        log_error(result)

    log_tool_result(name, result)
    return result


# ---------------------------------------------------------------------------
# Local tool implementations
# ---------------------------------------------------------------------------

async def _execute_local(
    name: str,
    args: dict[str, Any],
    *,
    session_store: SessionStore,
    api: SpaceMoltAPI,
    code_executor: CodeExecutor,
    force_credentials: bool,
    wiki: "WikiStore | None" = None,
) -> str:
    if name == "save_credentials":
        creds = Credentials(
            username=args.get("username", ""),
            password=args.get("password", ""),
            empire=args.get("empire", ""),
            player_id=args.get("player_id", ""),
        )
        ok = session_store.save_credentials(creds, force=force_credentials)
        # Also set on the API client for auto-reconnect
        if creds.username and creds.password:
            api.set_credentials(creds.username, creds.password)
        return "Credentials saved." if ok else "Credentials already exist (use --force-credentials)."

    if name == "update_todo":
        content = args.get("content", "")
        session_store.write_todo(content)
        return "TODO updated."

    if name == "read_todo":
        todo = session_store.read_todo()
        return todo or "(empty TODO list)"

    if name == "status_log":
        from spacemolt.ui import log_info
        msg = args.get("message", "")
        log_info(f"[Agent] {msg}")
        return "Logged."

    if name == "execute_code":
        code = args.get("code", "")
        if not code:
            return "Error: no code provided"
        try:
            return await code_executor.execute(code)
        except CodeExecutionError as exc:
            return f"Code execution error: {exc}"

    if name == "execute_sequence":
        sequence_name = args.get("sequence", "")
        params = args.get("params") or {}
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                return "Error: 'params' must be a valid JSON object"
        if not sequence_name:
            return "Error: 'sequence' parameter is required"
        return await run_sequence(api, sequence_name, params)

    # ------------------------------------------------------------------
    # Wiki tool
    # ------------------------------------------------------------------
    if name == "query_wiki":
        if not wiki:
            return "Wiki not initialized."
        question = args.get("question", args.get("query", ""))
        if not question:
            # Return stats
            return json_to_yaml(wiki.get_stats())
        return wiki.query(question)

    # ------------------------------------------------------------------
    # Crafting tools
    # ------------------------------------------------------------------
    if name == "get_recipes":
        from spacemolt.crafting import get_crafting_recipes
        return await get_crafting_recipes(
            api,
            category=args.get("category"),
            search=args.get("search"),
            page=args.get("page", 1),
            page_size=args.get("page_size", 20),
        )

    if name == "check_materials":
        from spacemolt.crafting import check_crafting_materials
        recipe_id = args.get("recipe_id", "")
        if not recipe_id:
            return "Error: 'recipe_id' is required"
        return await check_crafting_materials(
            api, recipe_id, quantity=args.get("quantity", 1),
        )

    if name == "craft_item":
        from spacemolt.crafting import craft_item
        recipe_id = args.get("recipe_id", "")
        if not recipe_id:
            return "Error: 'recipe_id' is required"
        return await craft_item(
            api, recipe_id,
            quantity=args.get("quantity", 1),
            deliver_to=args.get("deliver_to"),
        )

    if name == "query_catalog":
        from spacemolt.crafting import query_catalog
        catalog_type = args.get("type", args.get("catalog_type", ""))
        if not catalog_type:
            return "Error: 'type' is required (recipes, items, modules, ship_classes, facility_types)"
        return await query_catalog(
            api, catalog_type,
            category=args.get("category"),
            search=args.get("search"),
            item_id=args.get("id"),
            tier=args.get("tier"),
            empire=args.get("empire"),
            page=args.get("page", 1),
            page_size=args.get("page_size", 20),
        )

    # ------------------------------------------------------------------
    # Intel tools
    # ------------------------------------------------------------------
    if name == "query_intel":
        from spacemolt.intel import query_intel
        return await query_intel(
            api,
            system_id=args.get("system_id"),
            system_name=args.get("system_name"),
            poi_type=args.get("poi_type"),
            resource_type=args.get("resource_type"),
        )

    if name == "query_trade_intel":
        from spacemolt.intel import query_trade_intel
        return await query_trade_intel(
            api,
            item_id=args.get("item_id"),
            base_id=args.get("base_id"),
            station_name=args.get("station_name"),
        )

    return f"Unknown local tool: {name}"
