"""Predefined game action sequences — token-efficient multi-step operations.

Instead of the LLM generating multiple individual tool calls for common
workflows, it selects a named sequence. Each sequence is a deterministic
Python function that executes a series of game-API calls in order, handling
intermediate results, errors, and retries.

Token savings: ~60-80% compared to the LLM orchestrating each step individually.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional

from spacemolt.api import SpaceMoltAPI
from spacemolt.ui import log_info, log_success, log_warning, log_error, json_to_yaml


# ---------------------------------------------------------------------------
# Sequence result
# ---------------------------------------------------------------------------

@dataclass
class SequenceResult:
    """Result of executing a game sequence."""
    success: bool
    summary: str
    steps_completed: int
    steps_total: int
    details: list[str]

    def to_string(self) -> str:
        """Format as compact string for LLM context."""
        status = "✅ SUCCESS" if self.success else "❌ FAILED"
        header = f"{status} ({self.steps_completed}/{self.steps_total} steps)"
        lines = [header, self.summary]
        if self.details:
            lines.append("Steps:")
            for d in self.details:
                lines.append(f"  • {d}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _exec(api: SpaceMoltAPI, command: str, args: dict | None = None) -> str:
    """Execute a game command and return the result string."""
    return await api.execute(command, args or {})


def _check_error(result: str) -> bool:
    """Return True if the result looks like an error."""
    lower = result.lower()
    return any(kw in lower for kw in ("error:", "failed", "not found", "cannot", "insufficient"))


# ---------------------------------------------------------------------------
# Sequence: fly_to_station
# ---------------------------------------------------------------------------

async def fly_to_station(
    api: SpaceMoltAPI,
    station_id: str,
    *,
    system_id: Optional[str] = None,
) -> SequenceResult:
    """Fly to a station and dock.

    Steps: (optional: jump to system) → travel to station → dock

    Args:
        api: Game API client.
        station_id: Target station ID or name.
        system_id: If the station is in a different system, jump there first.
    """
    details: list[str] = []
    steps_total = 3 if system_id else 2
    step = 0

    # Step 1 (optional): Jump to target system
    if system_id:
        step += 1
        result = await _exec(api, "spacemolt/jump", {"system_id": system_id})
        details.append(f"Jump to system {system_id}: {result[:120]}")
        if _check_error(result):
            return SequenceResult(False, f"Failed to jump to system {system_id}", step, steps_total, details)

    # Step 2: Travel to station
    step += 1
    result = await _exec(api, "spacemolt/travel", {"destination_id": station_id})
    details.append(f"Travel to station {station_id}: {result[:120]}")
    if _check_error(result):
        return SequenceResult(False, f"Failed to travel to station {station_id}", step, steps_total, details)

    # Step 3: Dock
    step += 1
    result = await _exec(api, "spacemolt/dock", {"station_id": station_id})
    details.append(f"Dock: {result[:120]}")
    if _check_error(result):
        return SequenceResult(False, f"Failed to dock at station {station_id}", step, steps_total, details)

    return SequenceResult(True, f"Docked at station {station_id}", step, steps_total, details)


# ---------------------------------------------------------------------------
# Sequence: mine_and_return
# ---------------------------------------------------------------------------

async def mine_and_return(
    api: SpaceMoltAPI,
    asteroid_field: str,
    home_station: str,
    *,
    mine_cycles: int = 3,
) -> SequenceResult:
    """Travel to asteroid field, mine ore, return to station.

    Steps: undock → travel to field → scan → mine (N cycles) → travel back → dock

    Args:
        api: Game API client.
        asteroid_field: Asteroid field POI ID.
        home_station: Station to return to after mining.
        mine_cycles: Number of mining cycles (default: 3).
    """
    details: list[str] = []
    steps_total = 4 + mine_cycles  # undock + travel + scan + mine*N + travel back + dock = 4+N
    step = 0

    # Step 1: Undock (if docked)
    step += 1
    result = await _exec(api, "spacemolt/undock")
    details.append(f"Undock: {result[:120]}")
    # Not failing on undock error — might already be undocked

    # Step 2: Travel to asteroid field
    step += 1
    result = await _exec(api, "spacemolt/travel", {"destination_id": asteroid_field})
    details.append(f"Travel to field: {result[:120]}")
    if _check_error(result):
        return SequenceResult(False, f"Failed to reach asteroid field", step, steps_total, details)

    # Step 3: Scan for resources
    step += 1
    result = await _exec(api, "spacemolt/scan")
    details.append(f"Scan: {result[:100]}")

    # Steps 4..N+3: Mine
    mined_count = 0
    for i in range(mine_cycles):
        step += 1
        result = await _exec(api, "spacemolt/mine")
        short = result[:100]
        details.append(f"Mine cycle {i+1}: {short}")
        if _check_error(result):
            details.append(f"Mining stopped after {mined_count} cycles")
            break
        mined_count += 1

    # Step N+4: Travel back to station
    step += 1
    result = await _exec(api, "spacemolt/travel", {"destination_id": home_station})
    details.append(f"Return to station: {result[:120]}")
    if _check_error(result):
        return SequenceResult(False, f"Mined {mined_count}x but failed to return", step, steps_total, details)

    # Step N+5: Dock
    step += 1
    result = await _exec(api, "spacemolt/dock", {"station_id": home_station})
    details.append(f"Dock: {result[:120]}")

    success = mined_count > 0
    return SequenceResult(
        success,
        f"Mined {mined_count}/{mine_cycles} cycles, returned to station",
        step, steps_total, details,
    )


# ---------------------------------------------------------------------------
# Sequence: trade_route
# ---------------------------------------------------------------------------

async def trade_route(
    api: SpaceMoltAPI,
    buy_station: str,
    sell_station: str,
    commodity: str,
    *,
    quantity: Optional[int] = None,
    buy_system: Optional[str] = None,
    sell_system: Optional[str] = None,
) -> SequenceResult:
    """Execute a full trade route: buy at one station, sell at another.

    Steps: fly_to_station(buy) → buy commodity → fly_to_station(sell) → sell commodity

    Args:
        api: Game API client.
        buy_station: Station to buy from.
        sell_station: Station to sell at.
        commodity: Item/commodity name to trade.
        quantity: Amount to buy (None = max affordable).
        buy_system: System of buy station (if cross-system trade).
        sell_system: System of sell station (if cross-system trade).
    """
    details: list[str] = []
    steps_total = 6  # approximate
    step = 0

    # Phase 1: Go to buy station
    buy_result = await fly_to_station(api, buy_station, system_id=buy_system)
    step += buy_result.steps_completed
    details.extend(buy_result.details)
    if not buy_result.success:
        return SequenceResult(False, f"Failed to reach buy station", step, steps_total, details)

    # Phase 2: Buy commodity
    step += 1
    buy_args: dict[str, Any] = {"item": commodity}
    if quantity is not None:
        buy_args["quantity"] = quantity
    result = await _exec(api, "spacemolt/buy", buy_args)
    details.append(f"Buy {commodity}: {result[:150]}")
    if _check_error(result):
        return SequenceResult(False, f"Failed to buy {commodity}", step, steps_total, details)

    # Phase 3: Undock from buy station
    step += 1
    await _exec(api, "spacemolt/undock")
    details.append("Undocked from buy station")

    # Phase 4: Go to sell station
    sell_result = await fly_to_station(api, sell_station, system_id=sell_system)
    step += sell_result.steps_completed
    details.extend(sell_result.details)
    if not sell_result.success:
        return SequenceResult(False, f"Bought {commodity} but failed to reach sell station", step, steps_total, details)

    # Phase 5: Sell commodity
    step += 1
    sell_args: dict[str, Any] = {"item": commodity}
    if quantity is not None:
        sell_args["quantity"] = quantity
    result = await _exec(api, "spacemolt/sell", sell_args)
    details.append(f"Sell {commodity}: {result[:150]}")
    if _check_error(result):
        return SequenceResult(False, f"Arrived but failed to sell {commodity}", step, steps_total, details)

    return SequenceResult(True, f"Trade route complete: bought & sold {commodity}", step, steps_total, details)


# ---------------------------------------------------------------------------
# Sequence: combat_patrol
# ---------------------------------------------------------------------------

async def combat_patrol(
    api: SpaceMoltAPI,
    zone: str,
    *,
    max_engagements: int = 3,
    stance: str = "fire",
) -> SequenceResult:
    """Patrol a combat zone: travel, scan, engage enemies.

    Steps: undock → travel to zone → scan → (attack + stance loop)

    Args:
        api: Game API client.
        zone: Combat zone POI ID.
        max_engagements: Max number of targets to engage.
        stance: Combat stance (fire/evade/brace/flee).
    """
    details: list[str] = []
    steps_total = 3 + max_engagements * 2
    step = 0

    # Step 1: Undock
    step += 1
    await _exec(api, "spacemolt/undock")
    details.append("Undocked")

    # Step 2: Travel to combat zone
    step += 1
    result = await _exec(api, "spacemolt/travel", {"destination_id": zone})
    details.append(f"Travel to zone: {result[:120]}")
    if _check_error(result):
        return SequenceResult(False, "Failed to reach combat zone", step, steps_total, details)

    # Step 3: Scan for targets
    step += 1
    result = await _exec(api, "spacemolt/scan")
    details.append(f"Scan: {result[:150]}")

    # Step 4..N: Engage targets
    kills = 0
    for i in range(max_engagements):
        # Set stance
        step += 1
        await _exec(api, "spacemolt_battle/stance", {"stance": stance})
        details.append(f"Stance set to {stance}")

        # Attack
        step += 1
        result = await _exec(api, "spacemolt/attack")
        details.append(f"Attack {i+1}: {result[:120]}")
        if _check_error(result):
            details.append("No more targets or combat ended")
            break
        kills += 1

    return SequenceResult(
        kills > 0,
        f"Combat patrol: {kills} engagements in zone {zone}",
        step, steps_total, details,
    )


# ---------------------------------------------------------------------------
# Sequence: repair_and_refuel
# ---------------------------------------------------------------------------

async def repair_and_refuel(
    api: SpaceMoltAPI,
    station: str,
    *,
    system_id: Optional[str] = None,
) -> SequenceResult:
    """Fly to a station, repair the ship, and refuel.

    Steps: fly_to_station → repair → refuel

    Args:
        api: Game API client.
        station: Station ID.
        system_id: Jump to this system first (if needed).
    """
    details: list[str] = []
    steps_total = 4
    step = 0

    # Phase 1: Go to station
    fly_result = await fly_to_station(api, station, system_id=system_id)
    step += fly_result.steps_completed
    details.extend(fly_result.details)
    if not fly_result.success:
        return SequenceResult(False, "Failed to reach station for repairs", step, steps_total, details)

    # Phase 2: Repair
    step += 1
    result = await _exec(api, "spacemolt/repair")
    details.append(f"Repair: {result[:120]}")
    repair_ok = not _check_error(result)

    # Phase 3: Refuel
    step += 1
    result = await _exec(api, "spacemolt/refuel")
    details.append(f"Refuel: {result[:120]}")
    refuel_ok = not _check_error(result)

    success = repair_ok or refuel_ok
    return SequenceResult(
        success,
        f"Repair: {'✅' if repair_ok else '❌'} | Refuel: {'✅' if refuel_ok else '❌'}",
        step, steps_total, details,
    )


# ---------------------------------------------------------------------------
# Sequence: sell_all_cargo
# ---------------------------------------------------------------------------

async def sell_all_cargo(
    api: SpaceMoltAPI,
    station: Optional[str] = None,
) -> SequenceResult:
    """Sell all cargo at the current (or specified) station.

    Steps: (optional: fly_to_station) → get_cargo → sell each item

    Args:
        api: Game API client.
        station: If provided, fly to this station first.
    """
    details: list[str] = []
    step = 0
    steps_total = 3

    # Optional: Fly to station
    if station:
        fly_result = await fly_to_station(api, station)
        step += fly_result.steps_completed
        details.extend(fly_result.details)
        if not fly_result.success:
            return SequenceResult(False, "Failed to reach station", step, steps_total, details)

    # Get cargo
    step += 1
    result = await _exec(api, "spacemolt/get_cargo")
    details.append(f"Cargo check: {result[:200]}")

    # Sell all
    step += 1
    result = await _exec(api, "spacemolt/sell", {"item": "all"})
    details.append(f"Sell all: {result[:150]}")

    success = not _check_error(result)
    return SequenceResult(success, f"Sell all cargo: {'done' if success else 'failed'}", step, steps_total, details)


# ---------------------------------------------------------------------------
# Sequence: explore_system
# ---------------------------------------------------------------------------

async def explore_system(
    api: SpaceMoltAPI,
    system_id: Optional[str] = None,
) -> SequenceResult:
    """Explore the current (or specified) system: get info, scan, check market.

    Steps: (optional: jump) → get_system → get_location → scan → view_market

    Args:
        api: Game API client.
        system_id: If provided, jump to this system first.
    """
    details: list[str] = []
    steps_total = 4 if system_id else 3
    step = 0

    # Optional: Jump to system
    if system_id:
        step += 1
        result = await _exec(api, "spacemolt/jump", {"system_id": system_id})
        details.append(f"Jump: {result[:120]}")
        if _check_error(result):
            return SequenceResult(False, f"Failed to jump to {system_id}", step, steps_total, details)

    # Get system info
    step += 1
    result = await _exec(api, "spacemolt/get_system")
    details.append(f"System info: {result[:200]}")

    # Get location
    step += 1
    result = await _exec(api, "spacemolt/get_location")
    details.append(f"Location: {result[:150]}")

    # Scan surroundings
    step += 1
    result = await _exec(api, "spacemolt/scan")
    details.append(f"Scan: {result[:150]}")

    return SequenceResult(True, "System exploration complete", step, steps_total, details)


# ---------------------------------------------------------------------------
# Sequence: accept_and_track_mission
# ---------------------------------------------------------------------------

async def accept_and_track_mission(
    api: SpaceMoltAPI,
    mission_id: Optional[str] = None,
) -> SequenceResult:
    """List available missions, accept one, and check objectives.

    Steps: get_missions → accept_mission → get_status

    Args:
        api: Game API client.
        mission_id: Specific mission to accept (None = list available missions only).
    """
    details: list[str] = []
    steps_total = 3
    step = 0

    # List missions
    step += 1
    result = await _exec(api, "spacemolt/get_missions")
    details.append(f"Available missions: {result[:250]}")

    if not mission_id:
        return SequenceResult(True, "Missions listed (none accepted)", step, steps_total, details)

    # Accept mission
    step += 1
    result = await _exec(api, "spacemolt/accept_mission", {"mission_id": mission_id})
    details.append(f"Accept mission: {result[:150]}")
    if _check_error(result):
        return SequenceResult(False, f"Failed to accept mission {mission_id}", step, steps_total, details)

    # Check status
    step += 1
    result = await _exec(api, "spacemolt/get_status")
    details.append(f"Status: {result[:200]}")

    return SequenceResult(True, f"Mission {mission_id} accepted", step, steps_total, details)


# ---------------------------------------------------------------------------
# Sequence: full_status_check
# ---------------------------------------------------------------------------

async def full_status_check(api: SpaceMoltAPI) -> SequenceResult:
    """Comprehensive status check: status, location, cargo, ship, skills.

    Steps: get_status → get_location → get_cargo → get_ship → get_skills

    Useful after login or when the LLM needs a full picture.
    All calls are queries (free, no tick cost).
    """
    details: list[str] = []
    steps_total = 5
    step = 0

    for cmd, label in [
        ("spacemolt/get_status", "Status"),
        ("spacemolt/get_location", "Location"),
        ("spacemolt/get_cargo", "Cargo"),
        ("spacemolt/get_ship", "Ship"),
        ("spacemolt/get_skills", "Skills"),
    ]:
        step += 1
        result = await _exec(api, cmd)
        details.append(f"{label}: {result[:200]}")

    return SequenceResult(True, "Full status check complete", step, steps_total, details)


# ---------------------------------------------------------------------------
# Sequence registry
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Crafting sequences
# ---------------------------------------------------------------------------

async def craft_blueprint(
    api: SpaceMoltAPI,
    recipe_id: str,
    quantity: int = 1,
    deliver_to: str = "cargo",
) -> SequenceResult:
    """Look up recipe, check materials, and craft."""
    details = []
    total = 3

    # 1. Look up recipe in catalog
    recipe_info = await _exec(api, "spacemolt_catalog/catalog", {"type": "recipes", "id": recipe_id})
    details.append(f"Recipe lookup: {recipe_info[:200]}")
    if _check_error(recipe_info):
        return SequenceResult(False, f"Recipe '{recipe_id}' not found", 1, total, details)

    # 2. Check cargo for materials
    cargo = await _exec(api, "spacemolt/get_cargo")
    details.append(f"Cargo check done")

    # 3. Craft
    craft_args: dict[str, Any] = {"recipe_id": recipe_id, "quantity": quantity}
    if deliver_to:
        craft_args["deliver_to"] = deliver_to
    craft_result = await _exec(api, "spacemolt/craft", craft_args)
    details.append(f"Craft result: {craft_result[:300]}")

    if _check_error(craft_result):
        return SequenceResult(False, f"Crafting failed: {craft_result[:200]}", 3, total, details)

    return SequenceResult(True, f"Crafted {recipe_id} ×{quantity}", 3, total, details)


async def gather_and_craft(
    api: SpaceMoltAPI,
    recipe_id: str,
    quantity: int = 1,
) -> SequenceResult:
    """Check materials, report what's missing, attempt craft."""
    details = []
    total = 4

    # 1. Get recipe details
    recipe_info = await _exec(api, "spacemolt_catalog/catalog", {"type": "recipes", "id": recipe_id})
    details.append(f"Recipe: {recipe_info[:200]}")

    # 2. Check cargo
    cargo = await _exec(api, "spacemolt/get_cargo")
    details.append(f"Cargo checked")

    # 3. Check storage
    storage = await _exec(api, "spacemolt_storage/view")
    details.append(f"Storage checked")

    # 4. Attempt craft (API auto-pulls from cargo → storage → faction storage)
    craft_result = await _exec(api, "spacemolt/craft", {"recipe_id": recipe_id, "quantity": quantity})
    details.append(f"Craft result: {craft_result[:300]}")

    if "missing_materials" in craft_result.lower():
        return SequenceResult(
            False,
            f"Missing materials for {recipe_id}. Details: {craft_result[:300]}",
            4, total, details,
        )
    if _check_error(craft_result):
        return SequenceResult(False, f"Crafting failed: {craft_result[:200]}", 4, total, details)

    return SequenceResult(True, f"Crafted {recipe_id} ×{quantity}", 4, total, details)


async def production_chain(
    api: SpaceMoltAPI,
    recipe_id: str,
    quantity: int = 1,
) -> SequenceResult:
    """Full production chain: discover recipe tree, check all materials, craft in order."""
    details = []
    steps = 0

    # 1. Get the target recipe
    recipe_info = await _exec(api, "spacemolt_catalog/catalog", {"type": "recipes", "id": recipe_id})
    details.append(f"Target recipe: {recipe_info[:200]}")
    steps += 1

    # 2. Get all recipes (to find sub-recipes)
    all_recipes = await _exec(api, "spacemolt_catalog/catalog", {"type": "recipes", "page_size": 50})
    details.append(f"Fetched recipe catalog")
    steps += 1

    # 3. Check current inventory
    cargo = await _exec(api, "spacemolt/get_cargo")
    details.append(f"Cargo checked")
    steps += 1

    storage = await _exec(api, "spacemolt_storage/view")
    details.append(f"Storage checked")
    steps += 1

    # 4. Attempt crafting the final product
    craft_result = await _exec(api, "spacemolt/craft", {"recipe_id": recipe_id, "quantity": quantity})
    details.append(f"Final craft: {craft_result[:300]}")
    steps += 1

    if _check_error(craft_result) or "missing_materials" in craft_result.lower():
        return SequenceResult(
            False,
            f"Production chain incomplete for {recipe_id}. Missing materials or sub-recipes needed. {craft_result[:200]}",
            steps, steps, details,
        )

    return SequenceResult(True, f"Production chain complete: {recipe_id} ×{quantity}", steps, steps, details)


async def catalog_sync(
    api: SpaceMoltAPI,
    types: str = "recipes,items,modules,ship_classes,facility_types",
) -> SequenceResult:
    """Sync game catalog data into the Wiki (all queries are free)."""
    type_list = [t.strip() for t in types.split(",")]
    details = []
    steps = 0

    for cat_type in type_list:
        page = 1
        total_fetched = 0
        while True:
            result = await _exec(api, "spacemolt_catalog/catalog", {
                "type": cat_type,
                "page": page,
                "page_size": 50,
            })
            steps += 1
            # Try to detect pagination end
            if "page" in result.lower() and ("total_pages" in result.lower() or "items:" in result.lower()):
                # Check if we got items
                if "items: []" in result or "items:\n- " not in result.lower():
                    break
            total_fetched += 1
            details.append(f"Synced {cat_type} page {page}")

            # Simple heuristic: if result mentions total_pages, try to parse
            if page >= 10:  # safety limit
                break
            if "total_pages: 1" in result or f"page: {page}\ntotal_pages: {page}" in result:
                break
            page += 1

    return SequenceResult(
        True,
        f"Catalog sync complete: {', '.join(type_list)} ({steps} queries)",
        steps, steps, details,
    )


SEQUENCE_REGISTRY: dict[str, dict[str, Any]] = {
    "fly_to_station": {
        "function": fly_to_station,
        "description": "Fly to a station and dock. Optional cross-system jump.",
        "params": {
            "station_id": {"type": "string", "required": True, "description": "Target station ID"},
            "system_id": {"type": "string", "required": False, "description": "Jump to this system first"},
        },
        "tick_cost": "2-3 (travel + dock, optional jump)",
        "example": "Fly to station ST-42 in system Sol",
    },
    "mine_and_return": {
        "function": mine_and_return,
        "description": "Undock, fly to asteroid field, scan, mine N cycles, return to station and dock.",
        "params": {
            "asteroid_field": {"type": "string", "required": True, "description": "Asteroid field POI ID"},
            "home_station": {"type": "string", "required": True, "description": "Station to return to"},
            "mine_cycles": {"type": "integer", "required": False, "description": "Number of mining cycles (default: 3)"},
        },
        "tick_cost": "5-8 (undock + travel + mine*N + return + dock)",
        "example": "Mine 5 cycles at asteroid field AF-7, return to station ST-3",
    },
    "trade_route": {
        "function": trade_route,
        "description": "Complete trade loop: fly to buy station, buy commodity, fly to sell station, sell.",
        "params": {
            "buy_station": {"type": "string", "required": True, "description": "Station to buy at"},
            "sell_station": {"type": "string", "required": True, "description": "Station to sell at"},
            "commodity": {"type": "string", "required": True, "description": "Commodity to trade"},
            "quantity": {"type": "integer", "required": False, "description": "Amount (default: max affordable)"},
            "buy_system": {"type": "string", "required": False, "description": "System of buy station"},
            "sell_system": {"type": "string", "required": False, "description": "System of sell station"},
        },
        "tick_cost": "6-10 (travel + buy + travel + sell)",
        "example": "Buy Iron Ore at station ST-1, sell at station ST-5",
    },
    "combat_patrol": {
        "function": combat_patrol,
        "description": "Patrol a combat zone: undock, travel, scan, engage up to N targets.",
        "params": {
            "zone": {"type": "string", "required": True, "description": "Combat zone POI ID"},
            "max_engagements": {"type": "integer", "required": False, "description": "Max targets to engage (default: 3)"},
            "stance": {"type": "string", "required": False, "description": "Combat stance: fire/evade/brace/flee (default: fire)"},
        },
        "tick_cost": "5-10 (undock + travel + scan + attacks)",
        "example": "Patrol combat zone CZ-12 with aggressive stance",
    },
    "repair_and_refuel": {
        "function": repair_and_refuel,
        "description": "Fly to a station, repair ship, and refuel.",
        "params": {
            "station": {"type": "string", "required": True, "description": "Station ID"},
            "system_id": {"type": "string", "required": False, "description": "Jump to this system first"},
        },
        "tick_cost": "4-5 (travel + dock + repair + refuel)",
        "example": "Repair and refuel at station ST-3",
    },
    "sell_all_cargo": {
        "function": sell_all_cargo,
        "description": "Sell all cargo at the current or specified station.",
        "params": {
            "station": {"type": "string", "required": False, "description": "Station to fly to first (optional)"},
        },
        "tick_cost": "1-3 (sell, optional travel + dock)",
        "example": "Sell all cargo at current station",
    },
    "explore_system": {
        "function": explore_system,
        "description": "Explore a system: get info, location, scan surroundings. All queries are free.",
        "params": {
            "system_id": {"type": "string", "required": False, "description": "System to jump to (optional)"},
        },
        "tick_cost": "0-1 (queries are free, optional jump costs 1 tick)",
        "example": "Explore the current system",
    },
    "accept_and_track_mission": {
        "function": accept_and_track_mission,
        "description": "List available missions, optionally accept one, check status.",
        "params": {
            "mission_id": {"type": "string", "required": False, "description": "Mission ID to accept (omit to just list)"},
        },
        "tick_cost": "0-1 (queries free, accept costs 1 tick)",
        "example": "List missions and accept mission M-15",
    },
    "full_status_check": {
        "function": full_status_check,
        "description": "Comprehensive status: status, location, cargo, ship, skills. All queries FREE.",
        "params": {},
        "tick_cost": "0 (all queries are free)",
        "example": "Get full status overview after login",
    },
    "craft_blueprint": {
        "function": None,  # placeholder, set below
        "description": "Look up a crafting recipe, check materials, and craft the item.",
        "params": {
            "recipe_id": {"type": "string", "required": True, "description": "Recipe ID from the catalog"},
            "quantity": {"type": "integer", "required": False, "description": "How many to craft (default 1)"},
            "deliver_to": {"type": "string", "required": False, "description": "cargo/storage/faction_storage"},
        },
        "tick_cost": "1-2 (catalog query free, craft costs 1 tick each)",
        "example": "Craft 5 Refined Iron",
    },
    "gather_and_craft": {
        "function": None,  # placeholder, set below
        "description": "Check materials for a recipe, mine/buy missing ones, then craft.",
        "params": {
            "recipe_id": {"type": "string", "required": True, "description": "Recipe ID to craft"},
            "quantity": {"type": "integer", "required": False, "description": "How many to craft (default 1)"},
        },
        "tick_cost": "Variable (depends on missing materials)",
        "example": "Gather materials and craft Steel Plate",
    },
    "production_chain": {
        "function": None,  # placeholder, set below
        "description": "Execute a complete production chain: discover recipe, check sub-recipes, gather, craft.",
        "params": {
            "recipe_id": {"type": "string", "required": True, "description": "Final product recipe ID"},
            "quantity": {"type": "integer", "required": False, "description": "How many to produce (default 1)"},
        },
        "tick_cost": "Variable (multi-step production)",
        "example": "Complete production chain for Advanced Hull Plate",
    },
    "catalog_sync": {
        "function": catalog_sync,
        "description": "Sync the full game catalog into the Wiki: recipes, items, modules, ships, facilities.",
        "params": {
            "types": {"type": "string", "required": False, "description": "Comma-separated types (default: all)"},
        },
        "tick_cost": "0 (all catalog queries are free)",
        "example": "Sync all catalog data into the Wiki",
    },
}

# Wire up crafting sequence functions
SEQUENCE_REGISTRY["craft_blueprint"]["function"] = craft_blueprint
SEQUENCE_REGISTRY["gather_and_craft"]["function"] = gather_and_craft
SEQUENCE_REGISTRY["production_chain"]["function"] = production_chain


def get_sequence_list_for_prompt() -> str:
    """Format the sequence registry for inclusion in the system prompt."""
    lines = ["Available sequences for the `execute_sequence` tool:\n"]
    for name, info in SEQUENCE_REGISTRY.items():
        params_str = ", ".join(
            f"{p}{'*' if meta.get('required') else ''}"
            for p, meta in info["params"].items()
        ) if info["params"] else "(no params)"
        lines.append(f"- **{name}**({params_str}): {info['description']}")
        lines.append(f"  Tick cost: {info['tick_cost']} | Example: \"{info['example']}\"")
    lines.append("\n* = required parameter")
    lines.append("\nUse `execute_sequence` instead of multiple individual `game` calls for these workflows.")
    return "\n".join(lines)


async def run_sequence(
    api: SpaceMoltAPI,
    sequence_name: str,
    params: dict[str, Any],
) -> str:
    """Execute a named sequence and return the result string.

    Args:
        api: Game API client.
        sequence_name: Name from SEQUENCE_REGISTRY.
        params: Parameters for the sequence.

    Returns:
        Formatted result string for LLM context.
    """
    if sequence_name not in SEQUENCE_REGISTRY:
        available = ", ".join(SEQUENCE_REGISTRY.keys())
        return f"Error: Unknown sequence '{sequence_name}'. Available: {available}"

    entry = SEQUENCE_REGISTRY[sequence_name]
    func = entry["function"]

    # Validate required params
    for param_name, param_meta in entry["params"].items():
        if param_meta.get("required") and param_name not in params:
            return f"Error: Missing required parameter '{param_name}' for sequence '{sequence_name}'"

    log_info(f"▶ Executing sequence: {sequence_name}")

    try:
        result: SequenceResult = await func(api, **params)
        output = result.to_string()
        if result.success:
            log_success(f"Sequence {sequence_name}: {result.summary}")
        else:
            log_warning(f"Sequence {sequence_name}: {result.summary}")
        return output
    except Exception as exc:
        log_error(f"Sequence {sequence_name} error: {exc}")
        return f"Error executing sequence '{sequence_name}': {exc}"
