"""Serve the built command center and API together on localhost."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--build", action="store_true", help="Install pinned frontend dependencies and build")
    args = parser.parse_args()
    os.chdir(root)
    if args.build or not (root / "frontend/dist/index.html").exists():
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if not npm:
            raise SystemExit("Node.js/npm required to build the frontend. Install Node 22+ then retry.")
        subprocess.run([npm, "--prefix", "frontend", "ci"], check=True)
        subprocess.run([npm, "--prefix", "frontend", "run", "build"], check=True)
    import uvicorn

    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=args.port)
