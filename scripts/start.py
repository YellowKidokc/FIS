from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.server import run


def _port_from_args(default: int = 61845) -> int:
    import os

    raw = None
    if len(sys.argv) > 1:
        raw = sys.argv[1]
    elif os.getenv("FIS_PORT"):
        raw = os.getenv("FIS_PORT")

    if not raw:
        return default

    try:
        port = int(raw)
    except ValueError:
        raise SystemExit(f"Invalid port: {raw}")

    if port < 1 or port > 65535:
        raise SystemExit(f"Port out of range: {port}")

    return port


if __name__ == "__main__":
    run(port=_port_from_args())
