"""Pydantic data models for SpaceMolt Commander."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# API Models
# ---------------------------------------------------------------------------

class ApiError(BaseModel):
    """Error payload returned by the SpaceMolt v2 API."""
    code: str
    message: str
    wait_seconds: Optional[float] = None


class ApiSession(BaseModel):
    """Server-side session handle."""
    id: str
    player_id: Optional[str] = Field(None, alias="playerId")
    created_at: str = Field(alias="createdAt")
    expires_at: str = Field(alias="expiresAt")

    model_config = {"populate_by_name": True}


class ApiResponse(BaseModel):
    """Unified response envelope from the SpaceMolt v2 API."""
    result: Optional[Any] = None               # human-readable text
    structured_content: Optional[Any] = Field(None, alias="structuredContent")
    notifications: Optional[list[Any]] = None
    session: Optional[ApiSession] = None
    error: Optional[ApiError] = None

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Session / Credentials
# ---------------------------------------------------------------------------

class Credentials(BaseModel):
    """Player login credentials (persisted per session)."""
    username: str
    password: str
    empire: str = ""
    player_id: str = ""


# ---------------------------------------------------------------------------
# Schema / Command Discovery
# ---------------------------------------------------------------------------

class GameCommandInfo(BaseModel):
    """A single game command extracted from the OpenAPI spec."""
    name: str                # e.g. "spacemolt/mine"
    description: str = ""
    is_mutation: bool = False  # True ⇒ costs 1 tick (10 s)


# ---------------------------------------------------------------------------
# LLM Routing
# ---------------------------------------------------------------------------

class TaskComplexity(str, Enum):
    """Classification of task complexity for LLM routing."""
    LOW = "low"          # simple API calls, status checks
    MEDIUM = "medium"    # multi-step plans, market analysis
    HIGH = "high"        # strategic decisions, code generation


class LLMBackend(str, Enum):
    """Available LLM backends."""
    LOCAL = "local"      # Ollama / local model
    CLOUD = "cloud"      # Abacus.AI / Anthropic / OpenAI


# ---------------------------------------------------------------------------
# Compaction
# ---------------------------------------------------------------------------

class CompactionState(BaseModel):
    """Tracks the context compaction state across turns."""
    summary: str = ""
    compacted_at: Optional[datetime] = None
    messages_compacted: int = 0


# ---------------------------------------------------------------------------
# Tool definitions (for LLM tool-calling schema)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "game",
            "description": (
                "Execute any SpaceMolt game command. "
                "Use the command list from the system prompt to pick the right command name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command path, e.g. 'spacemolt/mine' or 'spacemolt/get_status'.",
                    },
                    "args": {
                        "type": "object",
                        "description": "Key-value arguments for the command. Omit if none required.",
                        "additionalProperties": True,
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_credentials",
            "description": "Persist login credentials to disk so they survive restarts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                    "empire": {"type": "string"},
                    "player_id": {"type": "string"},
                },
                "required": ["username", "password"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_todo",
            "description": "Overwrite the agent's TODO list (markdown).",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Full markdown content for the TODO file.",
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_todo",
            "description": "Read the current TODO list.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "status_log",
            "description": "Log a status message visible to the human observer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Status text to display."},
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": (
                "Execute a Python snippet for local data processing. "
                "Use this to crunch large datasets locally instead of loading them into context. "
                "The variable 'api' is pre-bound to the game API client. "
                "Store your result in a variable named 'result'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute. Must set a 'result' variable.",
                    },
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_sequence",
            "description": (
                "Execute a predefined multi-step game sequence. "
                "Use this instead of multiple individual 'game' calls for common workflows. "
                "Each sequence handles errors, retries, and returns a summary. "
                "Available sequences: fly_to_station, mine_and_return, trade_route, "
                "combat_patrol, repair_and_refuel, sell_all_cargo, explore_system, "
                "accept_and_track_mission, full_status_check, craft_blueprint, "
                "gather_and_craft, production_chain, catalog_sync. "
                "See the system prompt for details on each sequence."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {
                        "type": "string",
                        "description": (
                            "Name of the sequence to execute. One of: "
                            "fly_to_station, mine_and_return, trade_route, "
                            "combat_patrol, repair_and_refuel, sell_all_cargo, "
                            "explore_system, accept_and_track_mission, full_status_check, "
                            "craft_blueprint, gather_and_craft, production_chain, catalog_sync."
                        ),
                    },
                    "params": {
                        "type": "object",
                        "description": "Parameters for the sequence. See system prompt for required/optional params.",
                        "additionalProperties": True,
                    },
                },
                "required": ["sequence"],
            },
        },
    },
    # ------------------------------------------------------------------
    # Wiki tool
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "query_wiki",
            "description": (
                "Query the agent's knowledge base (Wiki). The Wiki automatically collects data "
                "from all game interactions. Use this BEFORE making API calls to check if you "
                "already know the answer. Examples:\n"
                "- 'systems with asteroid_belt' → find mining locations\n"
                "- 'where did I mine Iron Ore' → mining history\n"
                "- 'best prices for Fuel' → market data\n"
                "- 'crafting recipes' → known recipes\n"
                "- 'stations in system X' → known stations\n"
                "- 'stats' → wiki statistics overview\n"
                "If no question is provided, returns wiki statistics."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Natural language question about the game world.",
                    },
                },
                "required": ["question"],
            },
        },
    },
    # ------------------------------------------------------------------
    # Crafting tools
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "get_recipes",
            "description": (
                "Fetch crafting recipes from the game catalog. "
                "Results are automatically stored in the Wiki."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category (e.g. 'ore', 'refined', 'component').",
                    },
                    "search": {
                        "type": "string",
                        "description": "Free-text search for recipe names.",
                    },
                    "page": {"type": "integer", "description": "Page number (default 1)."},
                    "page_size": {"type": "integer", "description": "Items per page (default 20)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_materials",
            "description": (
                "Check if you have enough materials to craft a recipe. "
                "Checks cargo and station storage."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "recipe_id": {
                        "type": "string",
                        "description": "The recipe ID from the catalog.",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "How many to craft (default 1).",
                    },
                },
                "required": ["recipe_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "craft_item",
            "description": (
                "Craft an item using a recipe. Costs 1 tick per craft. "
                "Materials are auto-pulled from cargo → storage → faction storage."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "recipe_id": {
                        "type": "string",
                        "description": "The recipe ID from the catalog.",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of crafts (default 1). Each costs 1 tick.",
                    },
                    "deliver_to": {
                        "type": "string",
                        "description": "Output destination: 'cargo', 'storage', or 'faction_storage'.",
                    },
                },
                "required": ["recipe_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_catalog",
            "description": (
                "Query the game catalog for items, recipes, modules, ship_classes, or facility_types. "
                "Results are stored in the Wiki for future reference."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Catalog type: 'items', 'recipes', 'modules', 'ship_classes', 'facility_types'.",
                    },
                    "category": {"type": "string", "description": "Filter by category."},
                    "search": {"type": "string", "description": "Free-text search."},
                    "id": {"type": "string", "description": "Fetch specific item by ID."},
                    "tier": {"type": "string", "description": "Filter by tier."},
                    "empire": {"type": "string", "description": "Filter by empire."},
                    "page": {"type": "integer"},
                    "page_size": {"type": "integer"},
                },
                "required": ["type"],
            },
        },
    },
    # ------------------------------------------------------------------
    # Intel tools
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "query_intel",
            "description": (
                "Query faction system intelligence. Free query — no tick cost. "
                "Returns info about systems, POIs, and resources shared by faction members."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "system_id": {"type": "string", "description": "Filter by system ID."},
                    "system_name": {"type": "string", "description": "Search by system name."},
                    "poi_type": {"type": "string", "description": "Filter by POI type (asteroid_belt, station, etc.)."},
                    "resource_type": {"type": "string", "description": "Filter by resource type."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_trade_intel",
            "description": (
                "Query faction trade intelligence. Free query — no tick cost. "
                "Returns market prices shared by faction members."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string", "description": "Filter by item ID."},
                    "base_id": {"type": "string", "description": "Filter by station/base ID."},
                    "station_name": {"type": "string", "description": "Search by station name."},
                },
            },
        },
    },
]
