import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional


def load_json(filepath: str) -> Dict[str, Any]:
    with open(filepath, "r") as f:
        return json.load(f)


def sanitize_value(val):
    """Sanitize values like floats for consistent JSON output."""
    if isinstance(val, float):
        return round(val, 4)
    return val


def compact_attributes(attributes_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Converts list of attribute dicts to compact mapping {attribute_id: {value}}."""
    compact = {}
    for attr in attributes_list:
        base_value = attr.get("base")
        if base_value is not None:
            compact[attr["id"]] = {"value": sanitize_value(base_value)}
    return compact


def compact_inventory(inventory_list: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group inventory items by type: hotbar (0–8), main (9–35), armor (-106+), etc."""
    grouped = { "hotbar": [], "main": [], "armor": [], "off_hand": [], "other": [] }

    for item in inventory_list:
        slot = item.get("Slot")
        entry = {
            "id": item.get("id"),
            "count": item.get("count", 1),
            **({"components": item["components"]} if "components" in item else {})
        }
        if 0 <= slot <= 8:
            grouped["hotbar"].append(entry | {"slot": slot})
        elif 9 <= slot <= 35:
            grouped["main"].append(entry | {"slot": slot})
        elif -106 <= slot <= -103:
            grouped["armor"].append(entry | {"slot": slot})
        elif slot == -1:
            grouped["off_hand"].append(entry | {"slot": slot})
        else:
            grouped["other"].append(entry | {"slot": slot})

    # Remove empty groups
    return {k: v for k, v in grouped.items() if v}


def compact_status_effects(effects: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Convert status effects to compact {effect_id: {duration, amplifier}} format."""
    return {
        effect["id"]: {
            "duration": effect.get("duration"),
            "amplifier": effect.get("amplifier")
        }
        for effect in effects
    }


def extract_player_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract compacted player schema components from raw data."""
    uuid_parts = data.get("UUID", [])
    uuid = "-".join(str(x) for x in uuid_parts) if uuid_parts else "unknown_player"

    schema = {
        "player.meta.json": {
            "uuid": uuid,
            "name": None,
            "game_mode": ["survival", "creative", "adventure", "spectator"][data.get("playerGameType", 0)],
            "first_join": "first_join" in data.get("Tags", []),
            "dimension": data.get("Dimension", "minecraft:overworld"),
            "spawn_point": [data.get("SpawnX"), data.get("SpawnY"), data.get("SpawnZ")],
            "last_death": data.get("LastDeathLocation", None),
        },
        "position.json": {
            "pos": data.get("Pos", []),
            "rotation": data.get("Rotation", []),
            "motion": data.get("Motion", []),
            "dimension": data.get("Dimension", "minecraft:overworld"),
            "on_ground": bool(data.get("OnGround", 1)),
        },
        "inventory.json": compact_inventory(data.get("Inventory", [])),
        "ender_chest.json": data.get("EnderItems", []),
        "status_effects.json": compact_status_effects(data.get("active_effects", [])),
        "attributes.json": compact_attributes(data.get("attributes", [])),
        "stats.json": {
            "health": sanitize_value(data.get("Health")),
            "air": data.get("Air"),
            "food": {
                "level": data.get("foodLevel"),
                "saturation": sanitize_value(data.get("foodSaturationLevel")),
                "exhaustion": sanitize_value(data.get("foodExhaustionLevel")),
            },
            "xp": {
                "level": data.get("XpLevel"),
                "total": data.get("XpTotal"),
                "progress": sanitize_value(data.get("XpP")),
            }
        },
        "advancements.json": data.get("advancements", {}),
        "recipe_book.json": data.get("recipeBook", {}),
        "scoreboard.json": {
            "score": data.get("Score")
        }
    }

    return {k: v for k, v in schema.items() if v is not None}


def write_schema(schema: Dict[str, Any], output_dir: str):
    """Write player schema JSON components to output directory."""
    os.makedirs(output_dir, exist_ok=True)
    for filename, content in schema.items():
        with open(Path(output_dir) / filename, "w") as f:
            json.dump(content, f, indent=2)
    print(f"✅ Schema written to: {output_dir}")


def convert_player_json(input_path: str, output_root: str = "players"):
    data = load_json(input_path)
    schema = extract_player_schema(data)
    uuid = schema["player.meta.json"]["uuid"]
    player_dir = Path(output_root) / uuid
    write_schema(schema, player_dir)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python convert_player_to_schema.py <player.json>")
    else:
        convert_player_json(sys.argv[1])
