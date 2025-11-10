import os
from pathlib import Path

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data")).resolve()

# Optional single-file recipes; or point to a folder of split recipe files
RECIPES_PATH = Path(os.environ.get("RECIPES_PATH", DATA_ROOT / "recipes" / "all_recipes.json")).resolve()

# Optional: small indices to speed up slice picking
INDICES_DIR = Path(os.environ.get("INDICES_DIR", DATA_ROOT / "indices")).resolve()

# Security (simple shared secret header)
API_TOKEN = os.environ.get("MCP_API_TOKEN")
