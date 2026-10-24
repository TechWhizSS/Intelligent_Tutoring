"""Check configured model access without buying a generation. Run from repo root."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.providers import check

result = check()
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(0 if result['configured'] else 2)
