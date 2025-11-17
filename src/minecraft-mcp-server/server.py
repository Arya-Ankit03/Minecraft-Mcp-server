import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal

from fastapi import FastAPI, HTTPException, Depends, Header, Body, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from convert_player import convert_player_json

from config import DATA_ROOT, RECIPES_PATH, INDICES_DIR, API_TOKEN

app = FastAPI(title="Minecraft MCP Server", version="0.1.0")

# -----------------------
# Auth (simple shared key)
# -----------------------
def check_auth(x_api_token: Optional[str] = Header(None)):
    if API_TOKEN and x_api_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


# -----------------------
# Utilities
# -----------------------
def json_load(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(str(path))
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@lru_cache(maxsize=256)
def _cached_load(path_str: str, mtime: float):
    return json_load(Path(path_str))

def load_json_cached(path: Path) -> Any:
    # Use file mtime to break cache when file changes
    stat = path.stat()
    return _cached_load(path.as_posix(), stat.st_mtime)

def player_dir(uuid: str) -> Path:
    p = DATA_ROOT / "players" / uuid
    if not p.exists():
        raise FileNotFoundError(f"Player dir not found: {p}")
    return p

def allow_doc_name(name: str) -> bool:
    return name in {
        "player.meta.json",
        "position.json",
        "inventory.json",
        "ender_chest.json",
        "status_effects.json",
        "attributes.json",
        "stats.json",
        "advancements.json",
        "recipe_book.json",
        "scoreboard.json",
    }

def pick_recipes_slice(recipes: Any, query: str, ingredient_or_item: Optional[str] = None) -> Any:
    """
    Very lightweight selective reducer for recipes.
    - If you maintain /indices/item_to_recipes.json, uwse it.
    - Otherwise do a tiny filter by item id mention in the query.
    """
    # Try index
    idx_file = INDICES_DIR / "item_to_recipes.json"
    if idx_file.exists():
        index = load_json_cached(idx_file)
        # naive extraction of item words like minecraft:iron_ingot
        candidates: List[str] = []
        if ingredient_or_item:
            candidates.append(ingredient_or_item)
        else:
            for token in query.replace(",", " ").split():
                if ":" in token:
                    candidates.append(token.strip().lower())
        result_ids = set()
        for tok in candidates:
            if tok in index:
                for rid in index[tok]:
                    result_ids.add(rid)
        if not result_ids:
            return {}  # nothing relevant
        # recipes file structure can vary; assume dict keyed by recipe id
        if isinstance(recipes, dict):
            return {rid: recipes.get(rid) for rid in result_ids if rid in recipes}
        return recipes  # fallback

    # Fallback heuristic: small filter through values
    if not isinstance(recipes, dict):
        return recipes
    lowered = query.lower()
    out = {}
    for rid, r in recipes.items():
        blob = json.dumps(r).lower()
        if ":" in lowered:
            # If query contains fqids, require match
            if any(tok in blob for tok in lowered.split()):
                out[rid] = r
        else:
            # If plain words, keep tiny subset
            keywords = ["craft", "smelt", "blast", "stonecut", "smith", "make", "recipe"]
            if any(k in lowered for k in keywords):
                out[rid] = r
    # Keep it small
    if len(out) > 120:
        # trim arbitrarily to keep context cheap
        return dict(list(out.items())[:120])
    return out


# -----------------------
# Models
# -----------------------
class AskRequest(BaseModel):
    player_uuid: str
    query: str
    need: Optional[List[Literal["player", "inventory", "ender_chest", "attributes", "effects", "stats", "advancements", "recipe_book", "scoreboard", "world", "recipes"]]] = None
    item_hint: Optional[str] = None  # e.g. "minecraft:iron_ingot" for recipes

class AskResponse(BaseModel):
    used_context: Dict[str, Any]
    composed_prompt: str
    answer: Optional[str] = None  # Fill if you wire a model call


# -----------------------
# Health + discovery
# -----------------------
@app.get("/health", dependencies=[Depends(check_auth)])
def health():
    return {"ok": True, "data_root": DATA_ROOT.as_posix()}

@app.get("/players", dependencies=[Depends(check_auth)])
def list_players():
    base = DATA_ROOT / "players"
    if not base.exists():
        return []
    return [p.name for p in base.iterdir() if p.is_dir()]

@app.get("/players/{uuid}/index", dependencies=[Depends(check_auth)])
def player_index(uuid: str):
    d = player_dir(uuid)
    return sorted([p.name for p in d.iterdir() if p.is_file()])


# -----------------------
# Slice endpoints
# -----------------------
@app.get("/players/{uuid}/{doc}", dependencies=[Depends(check_auth)])
def get_player_doc(uuid: str, doc: str):
    if not allow_doc_name(doc):
        raise HTTPException(status_code=404, detail=f"Unknown doc: {doc}")
    p = player_dir(uuid) / doc
    try:
        return load_json_cached(p)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Not found: {p}")

@app.get("/recipes", dependencies=[Depends(check_auth)])
def get_recipes_slice(q: Optional[str] = Query(None), item: Optional[str] = Query(None)):
    if not RECIPES_PATH.exists():
        raise HTTPException(status_code=404, detail="Recipes file not found")
    recipes = load_json_cached(RECIPES_PATH)
    if not q and not item:
        # Never return entire giant recipes file by default
        return {"note": "Provide ?q= or ?item= to receive a small filtered slice."}
    return pick_recipes_slice(recipes, q or "", item)

# (Add similar /world/* slice endpoints later if needed)


# -----------------------
# Smart chat endpoint
# -----------------------
def choose_needs(query: str) -> List[str]:
    q = query.lower()
    if any(k in q for k in ["craft", "recipe", "make", "how do i craft", "smelt", "smith", "stonecut", "trim"]):
        return ["recipes", "inventory"]  # recipes + what player has
    if any(k in q for k in ["where", "do i have", "how many", "inventory", "ender chest", "armor", "weapon"]):
        return ["inventory", "ender_chest", "attributes"]
    if any(k in q for k in ["health", "xp", "level", "hungry", "food", "saturation"]):
        return ["stats"]
    if any(k in q for k in ["effect", "potion", "buff", "debuff"]):
        return ["effects"]
    if any(k in q for k in ["advancement", "achievement"]):
        return ["advancements"]
    if any(k in q for k in ["known recipe", "unlocked"]):
        return ["recipe_book"]
    if any(k in q for k in ["score", "points", "objective"]):
        return ["scoreboard"]
    # fallback
    return ["player", "inventory"]

def build_prompt(context: Dict[str, Any], query: str) -> str:
    # Tiny, consistent instruction to keep the LLM grounded
    header = (
        "You are a Minecraft assistant. Use ONLY the provided JSON context.\n"
        "If information is missing, say what slice you need (e.g., REQUEST: recipes or REQUEST: players/<uuid>/inventory.json).\n\n"
        "Context:\n"
    )
    ctx_str = json.dumps(context, ensure_ascii=False, indent=2)
    return f"{header}{ctx_str}\n\nQuestion: {query}\nAnswer:"

@app.post("/chat/ask", response_model=AskResponse, dependencies=[Depends(check_auth)])
def chat_ask(req: AskRequest):
    # Decide which slices to include
    needs = req.need or choose_needs(req.query)

    # Load minimal slices
    used: Dict[str, Any] = {}

    # Player slices
    if any(n in needs for n in ["player", "inventory", "ender_chest", "attributes", "effects", "stats", "advancements", "recipe_book", "scoreboard"]):
        pdir = player_dir(req.player_uuid)
        # Map logical names -> file names
        mapping = {
            "player": "player.meta.json",
            "inventory": "inventory.json",
            "ender_chest": "ender_chest.json",
            "attributes": "attributes.json",
            "effects": "status_effects.json",
            "stats": "stats.json",
            "advancements": "advancements.json",
            "recipe_book": "recipe_book.json",
            "scoreboard": "scoreboard.json",
        }
        for need, fname in mapping.items():
            if need in needs:
                fpath = pdir / fname
                if fpath.exists():
                    used[need] = load_json_cached(fpath)

    # Recipes slice (always filtered)
    if "recipes" in needs:
        if RECIPES_PATH.exists():
            recipes = load_json_cached(RECIPES_PATH)
            used["recipes"] = pick_recipes_slice(recipes, req.query, req.item_hint)
        else:
            used["recipes"] = {"note": "recipes file not found on server"}

    # Compose prompt (you can pipe this to your model client)
    prompt = build_prompt(used, req.query)

    # If you want to call a model here, do it and set 'answer'.
    # Keeping it stubbed because model choice/keys vary.
    return AskResponse(used_context=used, composed_prompt=prompt, answer=None)

@app.post("/chat/convert", dependencies=[Depends(check_auth)])
def convert(req: ConvertRequest):
    try:
        player_file = DATA_ROOT / "player.json"
        result = convert_player_json(player_file)

    except Exception as e:
        raise HTTPException(500, detail=str(e))

if __name__ == "__main__":
    # When executed directly, start the uvicorn server so `python server.py` works.
    # This avoids requiring the user to invoke uvicorn from the CLI.
    print("Starting up")
    try:
        import uvicorn

        # Bind to all interfaces by default for convenience; use DATA_ROOT/ENV to change in production
        uvicorn.run(app, host="127.0.0.1", port=8000)
    except Exception as e:
        # If uvicorn is not installed or other error occurs, print helpful message
        print("Failed to start uvicorn:", e)
        print("Try installing dependencies (e.g. 'uvicorn[standard]') or run with your ASGI server.")