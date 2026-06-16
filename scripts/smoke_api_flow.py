from __future__ import annotations
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from urllib.parse import urlencode
from app.server import RiverHandler
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import Request, urlopen

HOST, PORT = "127.0.0.1", 8765

def call(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = Request(f"http://{HOST}:{PORT}{path}", data=data, method=method, headers={"Content-Type":"application/json"})
    with urlopen(req, timeout=10) as res:
        payload = json.loads(res.read().decode())
    assert payload["ok"], payload
    return payload["data"]

def main():
    server = ThreadingHTTPServer((HOST, PORT), RiverHandler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root/"a.txt").write_text("same"); (root/"b.txt").write_text("same"); (root/"notes.tmp").write_text("tmp")
            q = urlencode({"path": str(root)})
            call("GET", "/api/health")
            call("POST", "/api/scan", {"path": str(root)})
            recipes = call("GET", f"/api/recipes/next?{q}")
            recipe = recipes["recipe"]
            story = call("POST", "/api/storyboard/build", {"path": str(root), "recipe": recipe})
            plan = call("POST", "/api/action/plan", {"path": str(root), "block_id": recipe["block_id"], "action": recipe["action"], "note":"smoke"})
            call("POST", "/api/action/preview", {"plan_id": plan["plan_id"]})
            call("POST", "/api/action/approve", {"plan_id": plan["plan_id"], "approved": True})
            executed = call("POST", "/api/action/execute", {"plan_id": plan["plan_id"], "confirm_execute": True})
            assert "executed" in executed
            print("production API smoke flow passed", story["storyboard_id"])
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
if __name__ == "__main__": main()
