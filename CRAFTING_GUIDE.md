# SpaceMolt Crafting Guide

## Übersicht

Das Crafting-System ermöglicht es dem Commander-Agenten, Items aus Rohstoffen herzustellen. Es umfasst Rezept-Entdeckung, Material-Management und automatisierte Produktionsketten.

## Verfügbare Tools

### Einzelne Tools

| Tool | Tick-Kosten | Beschreibung |
|---|---|---|
| `get_recipes` | 0 (Query) | Crafting-Rezepte aus dem Katalog abrufen |
| `check_materials` | 0 (Query) | Prüfen ob Materialien für ein Rezept vorhanden |
| `craft_item` | 1 pro Craft | Item craften |
| `query_catalog` | 0 (Query) | Katalog durchsuchen (Items, Rezepte, Module, Schiffe, Facilities) |

### Sequences (Mehrstufige Workflows)

| Sequence | Tick-Kosten | Beschreibung |
|---|---|---|
| `craft_blueprint` | 1-2 | Rezept nachschlagen → Material prüfen → Craften |
| `gather_and_craft` | Variable | Inventar prüfen → Fehlende Materialien identifizieren → Craften |
| `production_chain` | Variable | Komplette Produktionskette mit Sub-Rezepten |
| `catalog_sync` | 0 | Gesamten Spielkatalog ins Wiki laden |

## Crafting-Workflow

### Schritt 1: Rezepte entdecken

```json
// Alle Rezepte abrufen
{"tool": "get_recipes"}

// Nach Kategorie filtern
{"tool": "get_recipes", "args": {"category": "refined"}}

// Nach Name suchen
{"tool": "get_recipes", "args": {"search": "Steel"}}
```

### Schritt 2: Materialien prüfen

```json
{"tool": "check_materials", "args": {"recipe_id": "refined_iron", "quantity": 5}}
```

Prüft automatisch:
- Cargo (aktuelles Schiff)
- Station Storage (wenn angedockt)
- Faction Storage

### Schritt 3: Craften

```json
{"tool": "craft_item", "args": {"recipe_id": "refined_iron", "quantity": 5}}
```

**Material-Reihenfolge**: Die API zieht Materialien automatisch in dieser Reihenfolge:
1. Cargo
2. Persönlicher Station Storage
3. Faction Storage

**Output-Ziel**: Standard ist Cargo, konfigurierbar:
```json
{"tool": "craft_item", "args": {"recipe_id": "refined_iron", "quantity": 5, "deliver_to": "storage"}}
```

## Sequences verwenden

### craft_blueprint — Rezept nachschlagen und craften

```json
{
  "tool": "execute_sequence",
  "args": {
    "sequence": "craft_blueprint",
    "params": {"recipe_id": "refined_iron", "quantity": 5}
  }
}
```

Schritte:
1. Rezept im Katalog nachschlagen
2. Cargo prüfen
3. Craften

### gather_and_craft — Inventar prüfen und craften

```json
{
  "tool": "execute_sequence",
  "args": {
    "sequence": "gather_and_craft",
    "params": {"recipe_id": "steel_plate", "quantity": 2}
  }
}
```

Schritte:
1. Rezept nachschlagen
2. Cargo prüfen
3. Storage prüfen
4. Craft-Versuch (meldet fehlende Materialien)

### production_chain — Komplette Produktionskette

```json
{
  "tool": "execute_sequence",
  "args": {
    "sequence": "production_chain",
    "params": {"recipe_id": "advanced_hull_plate"}
  }
}
```

Schritte:
1. Zielrezept laden
2. Gesamten Rezeptkatalog laden (für Sub-Rezepte)
3. Inventar prüfen (Cargo + Storage)
4. Craft-Versuch

### catalog_sync — Katalog ins Wiki laden

```json
{
  "tool": "execute_sequence",
  "args": {
    "sequence": "catalog_sync",
    "params": {"types": "recipes,items"}
  }
}
```

Verfügbare Katalog-Typen:
- `recipes` — Crafting-Rezepte
- `items` — Alle Items
- `modules` — Schiffsmodule
- `ship_classes` — Schiffsklassen mit Baumaterialien
- `facility_types` — Facility-Definitionen

## Wiki-Integration

### Automatische Speicherung

Jede Crafting-Aktion wird automatisch im Wiki gespeichert:
- Rezepte aus `catalog(type=recipes)` → `wiki.recipes`
- Craft-Ergebnisse → `wiki.crafting_history`
- Item-Informationen → `wiki.items`

### Wiki-Abfragen

```json
// Alle bekannten Rezepte
{"tool": "query_wiki", "args": {"question": "crafting recipes"}}

// Rezepte für ein bestimmtes Material
{"tool": "query_wiki", "args": {"question": "recipes using Iron Ore"}}

// Crafting-Historie
{"tool": "query_wiki", "args": {"question": "crafting history"}}
```

## Fehlerbehandlung

### Missing Materials

Wenn Materialien fehlen, gibt die API Details zurück:
```yaml
error:
  code: missing_materials
  details:
    - item_id: iron_ore
      item_name: Iron Ore
      need: 10
      have: 3
```

Der Agent sollte dann:
1. Fehlende Materialien identifizieren
2. Mining-Standorte aus Wiki abfragen
3. Mining-Sequence ausführen
4. Erneut craften

### Craft-Anforderungen

- Muss an einer Station angedockt sein
- Ausreichende Materialien in Cargo/Storage
- Korrekte Recipe-ID aus dem Katalog
- Jeder Craft kostet 1 Tick (10 Sekunden)

## Crafting-Tipps

1. **Wiki zuerst**: Immer `query_wiki("crafting recipes")` nutzen, bevor `get_recipes` aufgerufen wird
2. **Catalog Sync**: Einmal `catalog_sync` nach Login ausführen — danach sind alle Rezepte im Wiki
3. **Bulk Crafting**: Mehrere Einheiten gleichzeitig craften mit `quantity > 1`
4. **Storage nutzen**: Mit `deliver_to: "storage"` direkt in Station Storage liefern
5. **Skill-Bonus**: Höherer Crafting-Skill = Bonus-Output pro Craft
