"""LLM-Wiki Knowledge Base — learns from every game interaction.

Automatically extracts and stores structured knowledge from API responses:
- Systems, POIs, and resources
- Mining history (where, what, how much)
- Station services and locations
- Market prices and trends
- Crafting recipes
- Intel data

Persisted per-session as JSON under sessions/{username}/wiki.json.
"""

from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from spacemolt.ui import log_info, log_warning


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_MARKET_HISTORY = 20   # price snapshots per item/station
MAX_MINING_HISTORY = 200  # mining events


# ---------------------------------------------------------------------------
# Wiki Store
# ---------------------------------------------------------------------------

class WikiStore:
    """Persistent, structured knowledge base for the SpaceMolt agent."""

    def __init__(self, wiki_path: Path) -> None:
        self._path = wiki_path
        self._data: dict[str, Any] = self._default_data()
        self._dirty = False
        self._load()

    # ------------------------------------------------------------------
    # Default schema
    # ------------------------------------------------------------------

    @staticmethod
    def _default_data() -> dict[str, Any]:
        return {
            "meta": {
                "version": 1,
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
                "total_updates": 0,
            },
            "systems": {},          # system_id → SystemInfo
            "stations": {},         # base_id → StationInfo
            "items": {},            # item_id → ItemInfo
            "recipes": {},          # recipe_id → RecipeInfo
            "ship_classes": {},     # class_id → ShipClassInfo
            "modules": {},          # module_id → ModuleInfo
            "facility_types": {},   # type_id → FacilityTypeInfo
            "empires": {},          # empire_id → EmpireInfo
            "mining_history": [],   # [{timestamp, system, poi, resource, quantity, ...}]
            "crafting_history": [], # [{timestamp, recipe, quantity, outputs, ...}]
            "market_prices": {},    # station_id → {item_id → [{price, qty, timestamp}]}
            "intel": {              # intel data
                "system_intel": {},     # system_id → intel data
                "trade_intel": {},      # station_id → trade intel
            },
            "player": {             # player knowledge
                "skills": {},
                "visited_systems": [],
                "known_routes": [],
            },
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                # Merge with defaults to handle schema upgrades
                merged = self._default_data()
                _deep_merge(merged, raw)
                self._data = merged
                log_info(f"Wiki loaded: {self._path.name} ({self._data['meta'].get('total_updates', 0)} updates)")
            except Exception as exc:
                log_warning(f"Wiki load failed, starting fresh: {exc}")
                self._data = self._default_data()

    def save(self) -> None:
        """Persist wiki to disk."""
        if not self._dirty:
            return
        self._data["meta"]["updated_at"] = _now_iso()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
        self._dirty = False

    def _mark_dirty(self) -> None:
        self._dirty = True
        self._data["meta"]["total_updates"] = self._data["meta"].get("total_updates", 0) + 1

    # ------------------------------------------------------------------
    # Ingestion — called after every API response
    # ------------------------------------------------------------------

    def ingest_response(self, command: str, args: Optional[dict], result: Any, structured: Any) -> None:
        """Extract knowledge from a game API response and store it."""
        try:
            self._ingest_impl(command, args, result, structured)
        except Exception as exc:
            log_warning(f"Wiki ingest error for {command}: {exc}")

    def _ingest_impl(self, command: str, args: Optional[dict], result: Any, structured: Any) -> None:
        data = structured if isinstance(structured, dict) else {}
        result_data = result if isinstance(result, dict) else {}
        # Use whichever has data
        merged_data = {**result_data, **data} if data or result_data else {}

        cmd = command.strip("/").lower()

        # ---- Systems & Navigation ----
        if cmd in ("spacemolt/get_system", "spacemolt/survey_system"):
            self._ingest_system(merged_data)
        elif cmd == "spacemolt/get_map":
            self._ingest_map(merged_data)
        elif cmd == "spacemolt/get_poi":
            self._ingest_poi(merged_data)
        elif cmd == "spacemolt/get_base":
            self._ingest_station(merged_data)
        elif cmd in ("spacemolt/get_location", "spacemolt/travel", "spacemolt/jump"):
            self._ingest_location(merged_data)

        # ---- Mining ----
        elif cmd == "spacemolt/mine":
            self._ingest_mining(merged_data, args)

        # ---- Trading / Market ----
        elif cmd in ("spacemolt_market/view_market", "spacemolt/view_market"):
            self._ingest_market(merged_data)
        elif cmd in ("spacemolt_market/analyze_market", "spacemolt/analyze_market"):
            self._ingest_market_analysis(merged_data)
        elif cmd in ("spacemolt/buy", "spacemolt/sell"):
            self._ingest_trade(cmd, merged_data)

        # ---- Crafting ----
        elif cmd == "spacemolt/craft":
            self._ingest_craft(merged_data)
        elif cmd == "spacemolt_catalog/catalog":
            self._ingest_catalog(merged_data, args)

        # ---- Intel ----
        elif cmd in ("spacemolt_intel/query_intel",):
            self._ingest_intel(merged_data)
        elif cmd in ("spacemolt_intel/query_trade_intel",):
            self._ingest_trade_intel(merged_data)

        # ---- Player ----
        elif cmd in ("spacemolt/get_skills",):
            self._ingest_skills(merged_data)
        elif cmd in ("spacemolt/get_status", "spacemolt/get_state"):
            self._ingest_status(merged_data)
        elif cmd in ("spacemolt/get_ship",):
            self._ingest_ship(merged_data)
        elif cmd in ("spacemolt/get_cargo",):
            self._ingest_cargo(merged_data)
        elif cmd in ("spacemolt/get_empire_info",):
            self._ingest_empire(merged_data)

        # ---- Notifications (inline in responses) ----
        # Notifications are handled separately via ingest_notifications

        if self._dirty:
            self.save()

    def ingest_notifications(self, notifications: list[dict]) -> None:
        """Extract knowledge from game notifications."""
        try:
            for n in notifications:
                ntype = n.get("type", "")
                data = n.get("data", n)
                if ntype == "mining_yield" or "resource_name" in data:
                    self._ingest_mining_notification(data)
                elif ntype == "combat_update":
                    pass  # Could track combat stats
            if self._dirty:
                self.save()
        except Exception as exc:
            log_warning(f"Wiki notification ingest error: {exc}")

    # ------------------------------------------------------------------
    # Ingestion helpers
    # ------------------------------------------------------------------

    def _ingest_system(self, data: dict) -> None:
        sid = data.get("id") or data.get("system_id")
        if not sid:
            return
        systems = self._data["systems"]
        existing = systems.get(sid, {})
        entry = {
            "name": data.get("name", existing.get("name", "")),
            "empire": data.get("empire", existing.get("empire", "")),
            "security_status": data.get("security_status", existing.get("security_status", "")),
            "police_level": data.get("police_level", existing.get("police_level")),
            "connections": data.get("connections", existing.get("connections", [])),
            "updated_at": _now_iso(),
        }
        # Process POIs
        pois = data.get("pois", data.get("points_of_interest", []))
        if pois and isinstance(pois, list):
            poi_map = existing.get("pois", {})
            for poi in pois:
                pid = poi.get("id")
                if not pid:
                    continue
                poi_entry = {
                    "name": poi.get("name", ""),
                    "type": poi.get("type", ""),
                    "class": poi.get("class", ""),
                    "has_base": poi.get("has_base", False),
                    "base_id": poi.get("base_id", ""),
                    "base_name": poi.get("base_name", ""),
                    "position": poi.get("position"),
                    "online": poi.get("online"),
                }
                # Merge resources if present
                resources = poi.get("resources", [])
                if resources:
                    poi_entry["resources"] = {
                        r.get("resource_id", r.get("id", "")): {
                            "name": r.get("name", r.get("resource_name", "")),
                            "richness": r.get("richness", ""),
                            "remaining": r.get("remaining"),
                            "remaining_display": r.get("remaining_display", ""),
                            "updated_at": _now_iso(),
                        }
                        for r in resources if isinstance(r, dict)
                    }
                elif pid in poi_map and "resources" in poi_map[pid]:
                    poi_entry["resources"] = poi_map[pid]["resources"]
                poi_map[pid] = poi_entry

                # Track station
                if poi.get("has_base") and poi.get("base_id"):
                    self._ensure_station(poi["base_id"], {
                        "name": poi.get("base_name", ""),
                        "poi_id": pid,
                        "system_id": sid,
                    })
            entry["pois"] = poi_map

        systems[sid] = entry
        # Track visited
        visited = self._data["player"].setdefault("visited_systems", [])
        if sid not in visited:
            visited.append(sid)
        self._mark_dirty()

    def _ingest_map(self, data: dict) -> None:
        systems_list = data.get("systems", data.get("map", []))
        if not isinstance(systems_list, list):
            return
        for s in systems_list:
            if not isinstance(s, dict):
                continue
            sid = s.get("id") or s.get("system_id")
            if not sid:
                continue
            existing = self._data["systems"].get(sid, {})
            self._data["systems"][sid] = {
                **existing,
                "name": s.get("name", existing.get("name", "")),
                "empire": s.get("empire", existing.get("empire", "")),
                "visited": s.get("visited", existing.get("visited", False)),
                "visited_at": s.get("visited_at", existing.get("visited_at")),
                "connections": s.get("connections", existing.get("connections", [])),
            }
        self._mark_dirty()

    def _ingest_poi(self, data: dict) -> None:
        pid = data.get("id") or data.get("poi_id")
        sid = data.get("system_id")
        if not pid:
            return
        # Store as nested in system
        if sid and sid in self._data["systems"]:
            pois = self._data["systems"][sid].setdefault("pois", {})
            existing_poi = pois.get(pid, {})
            poi_entry = {
                **existing_poi,
                "name": data.get("name", existing_poi.get("name", "")),
                "type": data.get("type", existing_poi.get("type", "")),
                "class": data.get("class", existing_poi.get("class", "")),
                "description": data.get("description", existing_poi.get("description", "")),
                "has_base": data.get("has_base", existing_poi.get("has_base", False)),
                "base_id": data.get("base_id", existing_poi.get("base_id", "")),
                "position": data.get("position", existing_poi.get("position")),
                "updated_at": _now_iso(),
            }
            # Resources
            resources = data.get("resources", [])
            if resources and isinstance(resources, list):
                poi_entry["resources"] = {
                    r.get("resource_id", r.get("id", "")): {
                        "name": r.get("name", r.get("resource_name", "")),
                        "richness": r.get("richness", ""),
                        "remaining": r.get("remaining"),
                        "remaining_display": r.get("remaining_display", ""),
                        "updated_at": _now_iso(),
                    }
                    for r in resources if isinstance(r, dict)
                }
            pois[pid] = poi_entry
            self._mark_dirty()

    def _ingest_station(self, data: dict) -> None:
        bid = data.get("id") or data.get("base_id")
        if not bid:
            return
        existing = self._data["stations"].get(bid, {})
        self._data["stations"][bid] = {
            **existing,
            "name": data.get("name", existing.get("name", "")),
            "poi_id": data.get("poi_id", existing.get("poi_id", "")),
            "system_id": data.get("system_id", existing.get("system_id", "")),
            "faction_id": data.get("faction_id", existing.get("faction_id", "")),
            "empire": data.get("empire", existing.get("empire", "")),
            "defense_level": data.get("defense_level", existing.get("defense_level")),
            "fuel_capacity": data.get("fuel_capacity", existing.get("fuel_capacity")),
            "fuel_reserve": data.get("fuel_reserve", existing.get("fuel_reserve")),
            "fuel_price": data.get("fuel_price", existing.get("fuel_price")),
            "facilities": data.get("facilities", existing.get("facilities", [])),
            "services": data.get("services", existing.get("services", [])),
            "updated_at": _now_iso(),
        }
        self._mark_dirty()

    def _ingest_location(self, data: dict) -> None:
        sid = data.get("system_id") or data.get("system", {}).get("id")
        if sid:
            visited = self._data["player"].setdefault("visited_systems", [])
            if sid not in visited:
                visited.append(sid)
                self._mark_dirty()

    def _ingest_mining(self, data: dict, args: Optional[dict]) -> None:
        entry = {
            "timestamp": _now_iso(),
            "system_id": data.get("system_id", ""),
            "poi_id": data.get("poi_id", args.get("poi_id", "") if args else ""),
            "resource_id": data.get("resource_id", ""),
            "resource_name": data.get("resource_name", ""),
            "quantity": data.get("quantity", 0),
            "remaining": data.get("remaining"),
            "remaining_display": data.get("remaining_display", ""),
            "depletion_percent": data.get("depletion_percent"),
            "xp_gained": data.get("xp_gained"),
        }
        history = self._data["mining_history"]
        history.append(entry)
        # Trim
        if len(history) > MAX_MINING_HISTORY:
            self._data["mining_history"] = history[-MAX_MINING_HISTORY:]

        # Update resource tracking in system POI
        if entry["resource_id"] and entry["poi_id"]:
            self._update_resource_remaining(entry)
        self._mark_dirty()

    def _ingest_mining_notification(self, data: dict) -> None:
        """Process mining yield notification."""
        entry = {
            "timestamp": _now_iso(),
            "resource_id": data.get("resource_id", ""),
            "resource_name": data.get("resource_name", ""),
            "quantity": data.get("quantity", 0),
            "remaining": data.get("remaining"),
            "remaining_display": data.get("remaining_display", ""),
            "depletion_percent": data.get("depletion_percent"),
        }
        self._data["mining_history"].append(entry)
        if len(self._data["mining_history"]) > MAX_MINING_HISTORY:
            self._data["mining_history"] = self._data["mining_history"][-MAX_MINING_HISTORY:]
        self._mark_dirty()

    def _update_resource_remaining(self, mining_entry: dict) -> None:
        """Update resource remaining data in the system POI."""
        for sys_data in self._data["systems"].values():
            pois = sys_data.get("pois", {})
            if mining_entry["poi_id"] in pois:
                poi = pois[mining_entry["poi_id"]]
                resources = poi.setdefault("resources", {})
                rid = mining_entry["resource_id"]
                if rid in resources:
                    resources[rid]["remaining"] = mining_entry.get("remaining")
                    resources[rid]["remaining_display"] = mining_entry.get("remaining_display", "")
                    resources[rid]["updated_at"] = _now_iso()

    def _ingest_market(self, data: dict) -> None:
        station_id = data.get("station_id", data.get("base_id", ""))
        items_list = data.get("items", [])
        if not isinstance(items_list, list):
            return
        market = self._data["market_prices"]
        station_market = market.setdefault(station_id, {})
        for item in items_list:
            if not isinstance(item, dict):
                continue
            iid = item.get("item_id", "")
            if not iid:
                continue
            snapshots = station_market.setdefault(iid, [])
            snapshots.append({
                "item_name": item.get("item_name", ""),
                "category": item.get("category", ""),
                "buy_price": item.get("buy_price") or item.get("best_buy"),
                "sell_price": item.get("sell_price") or item.get("best_sell"),
                "buy_quantity": item.get("buy_quantity") or item.get("best_buy_qty"),
                "sell_quantity": item.get("sell_quantity") or item.get("best_sell_qty"),
                "timestamp": _now_iso(),
            })
            if len(snapshots) > MAX_MARKET_HISTORY:
                station_market[iid] = snapshots[-MAX_MARKET_HISTORY:]

            # Also update items catalog
            self._ensure_item(iid, {
                "name": item.get("item_name", ""),
                "category": item.get("category", ""),
            })
        self._mark_dirty()

    def _ingest_market_analysis(self, data: dict) -> None:
        insights = data.get("insights", [])
        if not isinstance(insights, list):
            return
        station = data.get("station", "")
        for insight in insights:
            if isinstance(insight, dict) and insight.get("item_id"):
                self._ensure_item(insight["item_id"], {
                    "name": insight.get("item", ""),
                    "category": insight.get("category", ""),
                })
        self._mark_dirty()

    def _ingest_trade(self, cmd: str, data: dict) -> None:
        # Just track item knowledge
        iid = data.get("item_id", "")
        if iid:
            self._ensure_item(iid, {
                "name": data.get("item_name", data.get("name", "")),
            })
            self._mark_dirty()

    def _ingest_craft(self, data: dict) -> None:
        entry = {
            "timestamp": _now_iso(),
            "recipe": data.get("recipe", ""),
            "recipe_id": data.get("recipe_id", ""),
            "quantity": data.get("quantity", 1),
            "outputs": data.get("outputs", []),
            "xp_gained": data.get("xp_gained"),
            "skill_level": data.get("skill_level"),
            "level_up": data.get("level_up", False),
        }
        self._data["crafting_history"].append(entry)
        self._mark_dirty()

    def _ingest_catalog(self, data: dict, args: Optional[dict]) -> None:
        cat_type = (args or {}).get("type", data.get("type", ""))
        items_list = data.get("items", [])
        if not isinstance(items_list, list):
            return

        target = None
        if cat_type == "recipes":
            target = self._data["recipes"]
        elif cat_type == "items":
            target = self._data["items"]
        elif cat_type == "modules":
            target = self._data["modules"]
        elif cat_type == "ship_classes":
            target = self._data["ship_classes"]
        elif cat_type == "facility_types":
            target = self._data["facility_types"]

        if target is None:
            return

        for item in items_list:
            if not isinstance(item, dict):
                continue
            iid = item.get("id", "")
            if not iid:
                continue
            existing = target.get(iid, {})
            target[iid] = {**existing, **item, "updated_at": _now_iso()}
        self._mark_dirty()

    def _ingest_intel(self, data: dict) -> None:
        intel_data = data.get("intel", data.get("results", []))
        if isinstance(intel_data, list):
            for entry in intel_data:
                if isinstance(entry, dict):
                    sid = entry.get("system_id", "")
                    if sid:
                        existing = self._data["intel"]["system_intel"].get(sid, {})
                        self._data["intel"]["system_intel"][sid] = {
                            **existing, **entry, "updated_at": _now_iso(),
                        }
        elif isinstance(intel_data, dict):
            sid = intel_data.get("system_id", "")
            if sid:
                self._data["intel"]["system_intel"][sid] = {
                    **intel_data, "updated_at": _now_iso(),
                }
        self._mark_dirty()

    def _ingest_trade_intel(self, data: dict) -> None:
        intel_data = data.get("intel", data.get("results", []))
        if isinstance(intel_data, list):
            for entry in intel_data:
                if isinstance(entry, dict):
                    station = entry.get("base_id", entry.get("station_id", ""))
                    if station:
                        existing = self._data["intel"]["trade_intel"].get(station, {})
                        self._data["intel"]["trade_intel"][station] = {
                            **existing, **entry, "updated_at": _now_iso(),
                        }
        self._mark_dirty()

    def _ingest_skills(self, data: dict) -> None:
        skills = data.get("skills", data)
        if isinstance(skills, dict):
            self._data["player"]["skills"] = skills
            self._mark_dirty()
        elif isinstance(skills, list):
            skill_map = {}
            for s in skills:
                if isinstance(s, dict) and s.get("id"):
                    skill_map[s["id"]] = s
            if skill_map:
                self._data["player"]["skills"] = skill_map
                self._mark_dirty()

    def _ingest_status(self, data: dict) -> None:
        # Extract location info
        location = data.get("location", {})
        if isinstance(location, dict):
            sid = location.get("system_id")
            if sid:
                visited = self._data["player"].setdefault("visited_systems", [])
                if sid not in visited:
                    visited.append(sid)
                    self._mark_dirty()

    def _ingest_ship(self, data: dict) -> None:
        ship_class = data.get("ship_class", data.get("class", ""))
        if ship_class:
            self._ensure_item(ship_class, {
                "name": data.get("ship_name", data.get("name", "")),
                "category": "ship",
            })

    def _ingest_cargo(self, data: dict) -> None:
        items_list = data.get("items", data.get("cargo", []))
        if isinstance(items_list, list):
            for item in items_list:
                if isinstance(item, dict) and item.get("item_id"):
                    self._ensure_item(item["item_id"], {
                        "name": item.get("name", item.get("item_name", "")),
                        "category": item.get("category", ""),
                    })

    def _ingest_empire(self, data: dict) -> None:
        eid = data.get("id") or data.get("empire_id")
        if not eid:
            return
        self._data["empires"][eid] = {
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "bonuses": data.get("bonuses", ""),
            "home_systems": data.get("home_systems", []),
            "updated_at": _now_iso(),
        }
        self._mark_dirty()

    # ------------------------------------------------------------------
    # Helpers for ensuring catalog entries
    # ------------------------------------------------------------------

    def _ensure_item(self, item_id: str, info: dict) -> None:
        existing = self._data["items"].get(item_id, {})
        merged = {**existing}
        for k, v in info.items():
            if v:  # only overwrite with non-empty
                merged[k] = v
        self._data["items"][item_id] = merged

    def _ensure_station(self, base_id: str, info: dict) -> None:
        existing = self._data["stations"].get(base_id, {})
        merged = {**existing}
        for k, v in info.items():
            if v:
                merged[k] = v
        self._data["stations"][base_id] = merged

    # ------------------------------------------------------------------
    # Query Interface
    # ------------------------------------------------------------------

    def query(self, question: str) -> str:
        """Answer a natural-language question using wiki data.

        Supports structured queries like:
        - "systems with asteroid_belt"
        - "where did I mine Iron Ore"
        - "best prices for Fuel"
        - "crafting recipes"
        - "stations in system X"
        """
        q = question.lower().strip()

        # Route to specific handlers
        if any(kw in q for kw in ("asteroid", "belt", "nebula", "planet", "moon", "station")):
            return self._query_poi_by_type(q)
        if any(kw in q for kw in ("mine", "mining", "abgebaut", "mined")):
            return self._query_mining(q)
        if any(kw in q for kw in ("preis", "price", "market", "markt", "günstig", "cheap", "best")):
            return self._query_prices(q)
        if any(kw in q for kw in ("recipe", "rezept", "craft", "craften")):
            return self._query_recipes(q)
        if any(kw in q for kw in ("system", "systeme")):
            return self._query_systems(q)
        if any(kw in q for kw in ("station", "dock", "base")):
            return self._query_stations(q)
        if any(kw in q for kw in ("item", "resource", "material")):
            return self._query_items(q)
        if any(kw in q for kw in ("skill",)):
            return self._query_skills()
        if any(kw in q for kw in ("intel",)):
            return self._query_intel_data(q)
        if any(kw in q for kw in ("ship", "schiff")):
            return self._query_ships(q)
        if any(kw in q for kw in ("module", "mod")):
            return self._query_modules(q)
        if any(kw in q for kw in ("facility", "facilities")):
            return self._query_facilities(q)
        if any(kw in q for kw in ("stats", "statistik", "summary", "overview", "überblick")):
            return self._query_stats()

        # Fallback: search all text
        return self._full_text_search(q)

    def get_stats(self) -> dict:
        """Return wiki statistics."""
        return {
            "systems": len(self._data["systems"]),
            "stations": len(self._data["stations"]),
            "items": len(self._data["items"]),
            "recipes": len(self._data["recipes"]),
            "ship_classes": len(self._data["ship_classes"]),
            "modules": len(self._data["modules"]),
            "facility_types": len(self._data["facility_types"]),
            "mining_events": len(self._data["mining_history"]),
            "crafting_events": len(self._data["crafting_history"]),
            "market_stations_tracked": len(self._data["market_prices"]),
            "intel_systems": len(self._data["intel"]["system_intel"]),
            "total_updates": self._data["meta"].get("total_updates", 0),
        }

    # ------------------------------------------------------------------
    # Query implementations
    # ------------------------------------------------------------------

    def _query_poi_by_type(self, q: str) -> str:
        """Find systems containing specific POI types."""
        # Determine target type
        poi_type = None
        for t in ("asteroid_belt", "nebula", "planet", "moon", "station", "gate", "anomaly"):
            if t.replace("_", " ") in q or t in q:
                poi_type = t
                break

        results = []
        for sid, sdata in self._data["systems"].items():
            pois = sdata.get("pois", {})
            for pid, pdata in pois.items():
                if poi_type and pdata.get("type", "").lower() != poi_type:
                    continue
                if not poi_type:
                    # Match on any term in query
                    poi_str = json.dumps(pdata).lower()
                    if not any(w in poi_str for w in q.split() if len(w) > 3):
                        continue
                entry = f"- {sdata.get('name', sid)}/{pdata.get('name', pid)} (type={pdata.get('type')}"
                if pdata.get("resources"):
                    res_names = [r.get("name", rid) for rid, r in pdata["resources"].items()]
                    entry += f", resources: {', '.join(res_names)}"
                entry += ")"
                results.append(entry)

        if not results:
            return f"No POIs of type '{poi_type or 'matching'}' found in wiki. Try exploring more systems."
        return f"Found {len(results)} matching POIs:\n" + "\n".join(results[:50])

    def _query_mining(self, q: str) -> str:
        """Query mining history."""
        history = self._data["mining_history"]
        if not history:
            return "No mining history recorded yet."

        # Filter by resource name if mentioned
        resource_filter = None
        for word in q.split():
            if len(word) > 3 and word not in ("mine", "mining", "where", "mined", "abgebaut", "habe", "iron"):
                resource_filter = word
                break
        # Also check multi-word like "iron ore"
        for name in ("iron ore", "copper ore", "titanium", "gold", "silver", "platinum", "crystal"):
            if name in q:
                resource_filter = name
                break

        filtered = history
        if resource_filter:
            filtered = [h for h in history if resource_filter in (h.get("resource_name", "")).lower()]

        if not filtered:
            return f"No mining records matching '{resource_filter}'. Total mining events: {len(history)}"

        # Aggregate by resource
        by_resource: dict[str, dict] = {}
        for h in filtered:
            rname = h.get("resource_name", "Unknown")
            if rname not in by_resource:
                by_resource[rname] = {"total": 0, "count": 0, "locations": set()}
            by_resource[rname]["total"] += h.get("quantity", 0)
            by_resource[rname]["count"] += 1
            loc = h.get("poi_id") or h.get("system_id") or "unknown"
            by_resource[rname]["locations"].add(loc)

        lines = [f"Mining History ({len(filtered)} events):"]
        for rname, stats in by_resource.items():
            locs = ", ".join(list(stats["locations"])[:5])
            lines.append(f"- {rname}: {stats['total']} total ({stats['count']} events) at [{locs}]")
        return "\n".join(lines)

    def _query_prices(self, q: str) -> str:
        """Query market prices."""
        market = self._data["market_prices"]
        if not market:
            return "No market data recorded yet. Visit stations and check markets."

        # Find item filter
        item_filter = None
        for name_candidate in q.split():
            if len(name_candidate) > 3 and name_candidate not in (
                "price", "prices", "preis", "preise", "best", "cheap", "günstig",
                "market", "markt", "station", "where", "welche"
            ):
                item_filter = name_candidate
                break

        results = []
        for station_id, items in market.items():
            station_name = self._data["stations"].get(station_id, {}).get("name", station_id)
            for iid, snapshots in items.items():
                if not snapshots:
                    continue
                latest = snapshots[-1]
                iname = latest.get("item_name", iid)
                if item_filter and item_filter not in iname.lower() and item_filter not in iid.lower():
                    continue
                results.append({
                    "station": station_name,
                    "station_id": station_id,
                    "item": iname,
                    "buy": latest.get("buy_price"),
                    "sell": latest.get("sell_price"),
                    "timestamp": latest.get("timestamp", ""),
                })

        if not results:
            return f"No price data for '{item_filter or 'any item'}'. Visit more station markets."

        # Sort by sell price (best sell)
        results.sort(key=lambda x: x.get("sell") or 0, reverse=True)

        lines = [f"Market prices ({len(results)} entries):"]
        for r in results[:30]:
            lines.append(f"- {r['item']} @ {r['station']}: buy={r['buy']}, sell={r['sell']}")
        return "\n".join(lines)

    def _query_recipes(self, q: str) -> str:
        """Query crafting recipes."""
        recipes = self._data["recipes"]
        if not recipes:
            return "No crafting recipes in wiki. Use catalog(type='recipes') to load them."

        results = []
        for rid, rdata in recipes.items():
            if isinstance(rdata, dict):
                name = rdata.get("name", rid)
                inputs = rdata.get("inputs", rdata.get("materials", []))
                outputs = rdata.get("outputs", rdata.get("products", []))
                results.append(f"- **{name}** (id={rid})")
                if inputs:
                    in_str = ", ".join(
                        f"{i.get('name', i.get('item_id', '?'))}×{i.get('quantity', '?')}"
                        for i in (inputs if isinstance(inputs, list) else [])
                    )
                    results.append(f"  Inputs: {in_str}")
                if outputs:
                    out_str = ", ".join(
                        f"{o.get('name', o.get('item_id', '?'))}×{o.get('quantity', '?')}"
                        for o in (outputs if isinstance(outputs, list) else [])
                    )
                    results.append(f"  Outputs: {out_str}")

        if not results:
            return "No recipes match your query."
        return f"Known Recipes ({len(recipes)}):\n" + "\n".join(results[:60])

    def _query_systems(self, q: str) -> str:
        systems = self._data["systems"]
        if not systems:
            return "No systems in wiki. Explore the galaxy!"
        lines = [f"Known Systems ({len(systems)}):"]
        for sid, sdata in list(systems.items())[:50]:
            name = sdata.get("name", sid)
            empire = sdata.get("empire", "?")
            n_pois = len(sdata.get("pois", {}))
            lines.append(f"- {name} (empire={empire}, pois={n_pois})")
        return "\n".join(lines)

    def _query_stations(self, q: str) -> str:
        stations = self._data["stations"]
        if not stations:
            return "No stations in wiki."
        lines = [f"Known Stations ({len(stations)}):"]
        for bid, sdata in list(stations.items())[:50]:
            name = sdata.get("name", bid)
            system = sdata.get("system_id", "?")
            lines.append(f"- {name} (system={system}, id={bid})")
        return "\n".join(lines)

    def _query_items(self, q: str) -> str:
        items = self._data["items"]
        if not items:
            return "No items in wiki. Use catalog(type='items') to load them."
        lines = [f"Known Items ({len(items)}):"]
        for iid, idata in list(items.items())[:50]:
            name = idata.get("name", iid) if isinstance(idata, dict) else iid
            cat = idata.get("category", "") if isinstance(idata, dict) else ""
            lines.append(f"- {name} (id={iid}, cat={cat})")
        return "\n".join(lines)

    def _query_skills(self) -> str:
        skills = self._data["player"].get("skills", {})
        if not skills:
            return "No skill data. Use get_skills to fetch."
        lines = ["Player Skills:"]
        for sid, sdata in skills.items():
            if isinstance(sdata, dict):
                lines.append(f"- {sdata.get('name', sid)}: level {sdata.get('level', '?')}/{sdata.get('max_level', '?')}")
            else:
                lines.append(f"- {sid}: {sdata}")
        return "\n".join(lines)

    def _query_intel_data(self, q: str) -> str:
        si = self._data["intel"]["system_intel"]
        ti = self._data["intel"]["trade_intel"]
        lines = [f"Intel Data: {len(si)} system reports, {len(ti)} trade reports"]
        if si:
            lines.append("System Intel:")
            for sid, data in list(si.items())[:20]:
                lines.append(f"  - {sid}: {json.dumps(data)[:100]}")
        if ti:
            lines.append("Trade Intel:")
            for sid, data in list(ti.items())[:20]:
                lines.append(f"  - {sid}: {json.dumps(data)[:100]}")
        return "\n".join(lines)

    def _query_ships(self, q: str) -> str:
        ships = self._data["ship_classes"]
        if not ships:
            return "No ship classes in wiki. Use catalog(type='ship_classes') to load them."
        lines = [f"Known Ship Classes ({len(ships)}):"]
        for cid, cdata in list(ships.items())[:30]:
            name = cdata.get("name", cid) if isinstance(cdata, dict) else cid
            lines.append(f"- {name} (id={cid})")
        return "\n".join(lines)

    def _query_modules(self, q: str) -> str:
        modules = self._data["modules"]
        if not modules:
            return "No modules in wiki. Use catalog(type='modules') to load them."
        lines = [f"Known Modules ({len(modules)}):"]
        for mid, mdata in list(modules.items())[:30]:
            name = mdata.get("name", mid) if isinstance(mdata, dict) else mid
            lines.append(f"- {name} (id={mid})")
        return "\n".join(lines)

    def _query_facilities(self, q: str) -> str:
        facilities = self._data["facility_types"]
        if not facilities:
            return "No facility types in wiki. Use catalog(type='facility_types') to load them."
        lines = [f"Known Facility Types ({len(facilities)}):"]
        for fid, fdata in list(facilities.items())[:30]:
            name = fdata.get("name", fid) if isinstance(fdata, dict) else fid
            lines.append(f"- {name} (id={fid})")
        return "\n".join(lines)

    def _query_stats(self) -> str:
        stats = self.get_stats()
        lines = ["Wiki Statistics:"]
        for k, v in stats.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    def _full_text_search(self, q: str) -> str:
        """Fallback: search all wiki data as text."""
        terms = [w for w in q.split() if len(w) > 2]
        if not terms:
            return self._query_stats()

        matches = []
        # Search through all categories
        for category in ("systems", "stations", "items", "recipes", "ship_classes", "modules"):
            data = self._data.get(category, {})
            for eid, edata in data.items():
                text = json.dumps(edata, default=str).lower()
                if all(t in text for t in terms):
                    name = edata.get("name", eid) if isinstance(edata, dict) else eid
                    matches.append(f"- [{category}] {name} (id={eid})")

        if not matches:
            return f"No wiki entries matching '{q}'. The wiki has {self.get_stats()['systems']} systems and {self.get_stats()['items']} items."
        return f"Search results for '{q}' ({len(matches)} matches):\n" + "\n".join(matches[:30])

    # ------------------------------------------------------------------
    # Direct data access (for code executor)
    # ------------------------------------------------------------------

    @property
    def data(self) -> dict:
        """Direct access to raw wiki data."""
        return self._data


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override into base."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
