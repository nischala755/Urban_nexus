import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.sumo_adapter import run_validation

if __name__ == "__main__":
    path = Path("artifacts/sumo")
    path.mkdir(parents=True, exist_ok=True)
    report = run_validation(path)
    (path / "validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
