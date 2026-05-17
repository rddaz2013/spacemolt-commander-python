"""Intel system — query and submit system/trade intelligence.

The Intel system is the official faction-shared knowledge base in SpaceMolt.
Players submit intel about systems and trade prices, which is then available
to all faction members.

Endpoints:
- spacemolt_intel/submit_intel      — report system info (MUTATION)
- spacemolt_intel/query_intel       — query system intel (QUERY)
- spacemolt_intel/intel_status      — get intel status (QUERY)
- spacemolt_intel/submit_trade_intel — report trade prices (MUTATION)
- spacemolt_intel/query_trade_intel  — query trade intel (QUERY)
- spacemolt_intel/trade_intel_status — get trade intel status (QUERY)
"""

from __future__ import annotations

from typing import Any, Optional

from spacemolt.api import SpaceMoltAPI
from spacemolt.ui import log_info, log_success


# ---------------------------------------------------------------------------
# System Intel
# ---------------------------------------------------------------------------

async def query_intel(
    api: SpaceMoltAPI,
    *,
    system_id: Optional[str] = None,
    system_name: Optional[str] = None,
    poi_type: Optional[str] = None,
    resource_type: Optional[str] = None,
) -> str:
    """Query the faction's system intelligence database.

    Filters:
        system_id: Specific system to query
        system_name: Search by system name
        poi_type: Filter by POI type (asteroid_belt, station, etc.)
        resource_type: Filter by resource type
    """
    args: dict[str, Any] = {}
    if system_id:
        args["system_id"] = system_id
    if system_name:
        args["system_name"] = system_name
    if poi_type:
        args["poi_type"] = poi_type
    if resource_type:
        args["resource_type"] = resource_type

    log_info(f"Querying intel: {args or 'all'}")
    return await api.execute("spacemolt_intel/query_intel", args)


async def submit_intel(
    api: SpaceMoltAPI,
    systems: Optional[list[str]] = None,
) -> str:
    """Submit system intelligence from current/specified systems.

    This reports your scanned data to the faction intel database.
    Costs 1 tick.
    """
    args: dict[str, Any] = {}
    if systems:
        args["systems"] = systems

    log_info(f"Submitting system intel: {args or 'current system'}")
    result = await api.execute("spacemolt_intel/submit_intel", args)
    log_success("System intel submitted")
    return result


async def get_intel_status(api: SpaceMoltAPI) -> str:
    """Check the status of the intel system (contributions, rewards, etc.)."""
    log_info("Checking intel status")
    return await api.execute("spacemolt_intel/intel_status", {})


# ---------------------------------------------------------------------------
# Trade Intel
# ---------------------------------------------------------------------------

async def query_trade_intel(
    api: SpaceMoltAPI,
    *,
    item_id: Optional[str] = None,
    base_id: Optional[str] = None,
    station_name: Optional[str] = None,
) -> str:
    """Query the faction's trade intelligence database.

    Filters:
        item_id: Specific item to query prices for
        base_id: Specific station to query
        station_name: Search by station name
    """
    args: dict[str, Any] = {}
    if item_id:
        args["item_id"] = item_id
    if base_id:
        args["base_id"] = base_id
    if station_name:
        args["station_name"] = station_name

    log_info(f"Querying trade intel: {args or 'all'}")
    return await api.execute("spacemolt_intel/query_trade_intel", args)


async def submit_trade_intel(
    api: SpaceMoltAPI,
    stations: Optional[list[str]] = None,
) -> str:
    """Submit trade intelligence from current/specified stations.

    Reports market prices to the faction trade intel database.
    Costs 1 tick.
    """
    args: dict[str, Any] = {}
    if stations:
        args["stations"] = stations

    log_info(f"Submitting trade intel: {args or 'current station'}")
    result = await api.execute("spacemolt_intel/submit_trade_intel", args)
    log_success("Trade intel submitted")
    return result


async def get_trade_intel_status(api: SpaceMoltAPI) -> str:
    """Check trade intel system status."""
    log_info("Checking trade intel status")
    return await api.execute("spacemolt_intel/trade_intel_status", {})
