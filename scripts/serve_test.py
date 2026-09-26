"""An isolated browser-test server, never the interactive operator database."""

import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
os.chdir(root)
(root / "artifacts").mkdir(exist_ok=True)
os.environ["DATABASE_URL"] = "sqlite:///artifacts/e2e.db"

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8010)
