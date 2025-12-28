Minecraft MCP Server
=====================

Quick run instructions
----------------------

1. Create a virtual environment and activate it (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies with pip (recommended):

```powershell
python -m pip install --upgrade pip
python -m pip install "fastapi>=0.121.0" "fastmcp>=2.13.0.2" "pydantic>=2.5.3" "uvicorn[standard]>=0.22.0"
```

If you use an alternative package manager (you mentioned `uv`), install the same packages via that tool.

3. Run the server (development):

```powershell
# Option A: run directly as script
python server.py

# Option B: use uvicorn CLI for reload support
uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

4. Access the endpoints (example):

GET http://127.0.0.1:8000/health

Notes
-----
- The application reads data from `data/` by default; set `DATA_ROOT` env var to change this.
- To require a simple shared secret header, set the `MCP_API_TOKEN` environment variable; requests must include header `X-API-Token` with that value.
- If you want me to install dependencies in your environment and run the server here, tell me and I will do that.

