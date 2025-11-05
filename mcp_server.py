from fastmcp import FastMCP
from pathlib import Path
import json

# ===== Config =====
DATA_ROOT = Path("./data").resolve()
RECIPES_FILE = DATA_ROOT / "recipes" / "all_recipes.json"

def load_json(path: Path):
    if not path.exists():
        raise Exception(f"File not found: {path}")
    with open(path, "r") as f:
        return json.load(f)


# Create a FastMCP server instance and register resources/tools using the
# modern FastMCP API (v2+). This replaces the older top-level
# `resource`/`action` decorators that some examples used.

server = FastMCP(name="minecraft-mcp-server")


# ===== MCP Resources =====

@server.resource("resource://players/{uuid}/{part}")
def player(uuid: str, part: str):
    """Resource: Player data, get a part for a specific player

    Registered URI: resource://players/{uuid}/{part}
    """
    path = DATA_ROOT / "players" / uuid / f"{part}.json"
    return load_json(path)


@server.resource("resource://recipes/all")
def recipes():
    """Resource: All recipes (for now, entire file, or add filtering)

    Registered URI: resource://recipes/all
    """
    return load_json(RECIPES_FILE)


# ===== MCP Actions / Tools =====

@server.tool
def query_chat(player_uuid: str, query: str) -> str:
    """Tool: Chat-style query based on inventory + recipes

    This mirrors the old `@action` example but registers as a FastMCP tool.
    """
    player_data = load_json(DATA_ROOT / "players" / player_uuid / "inventory.json")
    recipe_data = load_json(RECIPES_FILE)

    prompt = (
        f"Player Inventory:\n{json.dumps(player_data, indent=2)}\n\n"
        f"Available Recipes:\n{json.dumps(recipe_data, indent=2)}\n\n"
        f"Question: {query}\nAnswer:"
    )

    # Stub: You can integrate an LLM here later
    return f"(AI Response Placeholder)\n\n{prompt}"


# ===== Run MCP Server =====

if __name__ == "__main__":
    print("Starting FastMCP server (HTTP transport) - use Ctrl+C to stop")
    # Start an HTTP transport using the FastMCP server's runner. This will
    # run a Uvicorn instance internally. If you prefer to expose an ASGI app
    # to be run by an external uvicorn process, let me know and I can add
    # an `app = ...` ASGI object export.
    server.run(transport="http", host="127.0.0.1", port=8000)
