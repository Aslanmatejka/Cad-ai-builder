"""
Start the Chat-to-CAD Platform Backend
Run this file to start the FastAPI server
"""

import sys
import os
import signal

# Fix Windows console encoding for emoji characters
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import uvicorn
from config import settings

if __name__ == "__main__":
    # On Windows, prevent CTRL_C_EVENT from parent console killing the server
    # (common issue in VS Code integrated terminals)
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, signal.SIG_IGN)

    print("=" * 60)
    print("Chat-to-CAD Platform - Phase 4")
    print("=" * 60)
    print(f"Geometry Engine: CadQuery")
    print(f"LLM: {settings.AI_MODEL_NAME}")
    print(f"Server: FastAPI on port {settings.PORT}")
    print("=" * 60)
    print(f"\nAPI: http://localhost:{settings.PORT}")
    print(f"Docs: http://localhost:{settings.PORT}/docs")
    print(f"Health: http://localhost:{settings.PORT}/\n")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        reload_delay=1.0,
        log_level="info",
    )
