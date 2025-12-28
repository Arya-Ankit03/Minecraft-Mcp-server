"""Minimal FastAPI app that responds to a GET request."""

from fastapi import FastAPI
from openai import OpenAI


app = FastAPI(title="SimpleFastAPI", version="0.1.0")


@app.get("/ping")
def ping() -> dict[str, str]:
    """Health-check endpoint that returns a friendly message."""
    return {"message": "pong"}


@app.get("askai")

def chat() -> dict[str,str]:
    pass

    

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