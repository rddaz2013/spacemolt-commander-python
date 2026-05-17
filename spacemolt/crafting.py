"""Crafting system — recipe discovery, material checking, and item crafting.

Endpoints used:
- POST /api/v2/spacemolt_catalog  (type="recipes") — discover recipes
- POST /api/v2/spacemolt/get_cargo — check materials in cargo
- POST /api/v2/spacemolt_storage/view — check station storage
- POST /api/v2/spacemolt/craft — craft an item (1 tick per craft)
"""

from __future__ import annotations

from typing import Any, Optional

from spacemolt.api import SpaceMoltAPI
from spacemolt.ui import log_info, log_warning, log_error, log_success, json_to_yaml


# ---------------------------------------------------------------------------
# Recipe discovery
# ---------------------------------------------------------------------------

async def get_crafting_recipes(
    api: SpaceMoltAPI,
    *,
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> str:
    """Fetch crafting recipes from the game catalog.

    Returns YAML-formatted recipe list.
    """
    args: dict[str, Any] = {"type": "recipes", "page": page, "page_size": page_size}
    if category:
        args["category"] = category
    if search:
        args["search"] = search

    log_info(f"Fetching crafting recipes (category={category}, search={search}, page={page})")
    result = await api.execute("spacemolt_catalog/catalog", args)
    return result


async def get_recipe_details(api: SpaceMoltAPI, recipe_id: str) -> str:
    """Fetch details for a specific recipe by ID."""
    log_info(f"Fetching recipe details: {recipe_id}")
    result = await api.execute("spacemolt_catalog/catalog", {
        "type": "recipes",
        "id": recipe_id,
    })
    return result


# ---------------------------------------------------------------------------
# Material checking
# ---------------------------------------------------------------------------

async def check_crafting_materials(
    api: SpaceMoltAPI,
    recipe_id: str,
    quantity: int = 1,
) -> str:
    """Check if the player has enough materials for a recipe.

    Checks both cargo and station storage. Returns a summary
    of what's available and what's missing.
    """
    log_info(f"Checking materials for recipe '{recipe_id}' ×{quantity}")

    # 1. Get recipe details
    recipe_result = await api.execute("spacemolt_catalog/catalog", {
        "type": "recipes",
        "id": recipe_id,
    })

    # 2. Get cargo
    cargo_result = await api.execute("spacemolt/get_cargo", {})

    # 3. Get storage (may fail if not at station)
    storage_result = ""
    try:
        storage_result = await api.execute("spacemolt_storage/view", {})
    except Exception:
        storage_result = "(not at a station or no storage access)"

    # Combine results
    lines = [
        f"=== Material Check for '{recipe_id}' ×{quantity} ===",
        "",
        "Recipe:",
        recipe_result[:1000],
        "",
        "Cargo:",
        cargo_result[:1000],
        "",
        "Storage:",
        str(storage_result)[:1000],
        "",
        "Note: The craft command auto-pulls from cargo → storage → faction storage.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Crafting execution
# ---------------------------------------------------------------------------

async def craft_item(
    api: SpaceMoltAPI,
    recipe_id: str,
    quantity: int = 1,
    deliver_to: Optional[str] = None,
) -> str:
    """Craft an item using a recipe.

    Args:
        recipe_id: The recipe ID from the catalog.
        quantity: Number of times to craft (each costs 1 tick).
        deliver_to: Where to put the output: 'cargo', 'storage', or 'faction_storage'.
    """
    args: dict[str, Any] = {
        "recipe_id": recipe_id,
        "quantity": quantity,
    }
    if deliver_to:
        args["deliver_to"] = deliver_to

    log_info(f"Crafting: recipe={recipe_id}, qty={quantity}, deliver_to={deliver_to or 'default'}")
    result = await api.execute("spacemolt/craft", args)

    # Check for success indicators
    if "missing_materials" in result.lower():
        log_warning(f"Crafting failed — missing materials for {recipe_id}")
    elif "error" in result.lower():
        log_error(f"Crafting error for {recipe_id}")
    else:
        log_success(f"Crafted {recipe_id} ×{quantity}")

    return result


# ---------------------------------------------------------------------------
# Catalog queries (items, modules, ships, facilities)
# ---------------------------------------------------------------------------

async def query_catalog(
    api: SpaceMoltAPI,
    catalog_type: str,
    *,
    category: Optional[str] = None,
    search: Optional[str] = None,
    item_id: Optional[str] = None,
    tier: Optional[str] = None,
    empire: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> str:
    """Query the game catalog for items, recipes, modules, ship_classes, or facility_types."""
    args: dict[str, Any] = {
        "type": catalog_type,
        "page": page,
        "page_size": page_size,
    }
    if category:
        args["category"] = category
    if search:
        args["search"] = search
    if item_id:
        args["id"] = item_id
    if tier:
        args["tier"] = tier
    if empire:
        args["empire"] = empire

    log_info(f"Catalog query: type={catalog_type}, search={search}, category={category}")
    return await api.execute("spacemolt_catalog/catalog", args)
