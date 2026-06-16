import json, sys
from core.orchestrator import run_folder_intelligence
print(json.dumps(run_folder_intelligence(sys.argv[1] if len(sys.argv) > 1 else "."), indent=2))
