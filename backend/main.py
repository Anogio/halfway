from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "shared" / "src"))

from transit_backend.api.server import app


if __name__ == "__main__":
    uvicorn.run("main:app", host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "8080")))
