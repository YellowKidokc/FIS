from __future__ import annotations
import json, sys, tempfile, time, socket
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from urllib.parse import urlencode
from app.server import RiverHandler
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import URLError

def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def _wait_ready(host, port, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.1):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"Server {host}:{port} did not become ready in {timeout}s")

def call(method, path, body=None, host="127.0.0.1", port=8765):
    data = None if body is None else json.dumps(body).encode()
    req = Request(f"http://{host}:{port}{path}", data=data, method=method, headers={"Content-Type":"application/json"})
    with urlopen(req, timeout=10) as res:
        payload = json.loads(res.read().decode())
    assert payload["ok"], payload
    return payload["data"]

def main():
    host = "127.0.0.1"
    port = _free_port()
    server = ThreadingHTTPServer((host, port), RiverHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _wait_ready(host, port)
    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root/"a.txt").write_text("same"); (root/"b.txt").write_text("same"); (root/"notes.tmp").write_text("tmp")
            q = urlencode({"path": str(root)})
            call("GET", "/api/health", host=host, port=port)
            call("POST", "/api/scan", {"path": str(root)}, host=host, port=port)
            recipes = call("GET", f"/api/recipes/next?{q}", host=host, port=port)
            recipe = recipes["recipe"]
            story = call("POST", "/api/storyboard/build", {"path": str(root), "recipe": recipe}, host=host, port=port)
            plan = call("POST", "/api/action/plan", {"path": str(root), "block_id": recipe["block_id"], "action": recipe["action"], "note":"smoke"}, host=host, port=port)
            call("POST", "/api/action/preview", {"plan_id": plan["plan_id"]}, host=host, port=port)
            call("POST", "/api/action/approve", {"plan_id": plan["plan_id"], "approved": True}, host=host, port=port)
            executed = call("POST", "/api/action/execute", {"plan_id": plan["plan_id"], "confirm_execute": True}, host=host, port=port)
            assert "executed" in executed
            print("production API smoke flow passed", story["storyboard_id"])
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)

if __name__ == "__main__": main()
