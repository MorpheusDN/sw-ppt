"""Local-only JSON API and offline Web frontend. Run: python server.py"""
from __future__ import annotations

import argparse
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from memory_engine import Engine, export_bundle

ROOT = Path(__file__).resolve().parent
MAX_BODY = 20 * 1024 * 1024


def create_server(data_path, port=8765, model_path=None, qa_model_path=None):
    data_path = Path(data_path)
    state = {"engine": Engine(json.loads(data_path.read_text(encoding="utf-8")), model_path)}
    lock = threading.RLock()
    answerer = None
    if qa_model_path:
        from local_models import OnnxAnswerer
        answerer = OnnxAnswerer(qa_model_path)

    class Handler(BaseHTTPRequestHandler):
        def send_json(self, data, status=200):
            body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path
            with lock:
                engine = state["engine"]
                if path == "/api/health":
                    return self.send_json({"status": "ok", "dataset_path": data_path.name, "vector_available": engine.dense is not None,
                                           "memory_count": len(engine.memories), "answer_model_available":answerer is not None,
                                           "mode": "local-coursework-prototype"})
                if path == "/api/conversations":
                    return self.send_json({"conversations": [{"conversation_id": c["conversation_id"], "sessions": len(c["sessions"]),
                                                               "turns": sum(len(s["turns"]) for s in c["sessions"])} for c in engine.conversations]})
                if path == "/api/export":
                    return self.send_json(export_bundle(engine))
                if path == "/api/memories":
                    cid = parse_qs(urlparse(self.path).query).get("conversation_id", [None])[0]
                    if cid not in [c["conversation_id"] for c in engine.conversations]:
                        return self.send_json({"error": "unknown conversation_id"}, 404)
                    return self.send_json({"memories": [m for m in engine.memories if m["conversation_id"] == cid]})
            files = {"/": ("index.html", "text/html"), "/style.css": ("style.css", "text/css"), "/app.js": ("app.js", "application/javascript"),
                     "/app.js.LEGAL.txt": ("app.js.LEGAL.txt", "text/plain")}
            if path not in files:
                return self.send_json({"error": "not found"}, 404)
            name, mime = files[path]
            body = (ROOT / "web" / name).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            path = urlparse(self.path).path
            if path not in ("/api/import", "/api/query"):
                return self.send_json({"error": "not found"}, 404)
            origin = self.headers.get("Origin")
            if origin and origin not in (f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"):
                return self.send_json({"error": "foreign origin rejected"}, 403)
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BODY:
                    return self.send_json({"error": "JSON body must be between 1 byte and 20 MiB"}, 413)
                payload = json.loads(self.rfile.read(size).decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("Expected an object")
                if path == "/api/import":
                    candidate = Engine(payload.get("data"), model_path)
                    with lock:
                        # Only commit valid imports. Original input files are never overwritten.
                        dest = ROOT / "data" / "imported.json"
                        dest.parent.mkdir(exist_ok=True)
                        temporary = dest.with_suffix(".tmp")
                        temporary.write_text(json.dumps(candidate.conversations, ensure_ascii=False, indent=2), encoding="utf-8")
                        os.replace(temporary, dest)
                        state["engine"] = candidate
                    return self.send_json({"imported_conversations": len(candidate.conversations), "memories": len(candidate.memories),
                                           "saved_to": "data/imported.json", "restart": "python server.py --data data/imported.json"})
                allowed = {"conversation_id", "question", "k", "as_of", "entity", "attribute", "method", "open_domain"}
                if set(payload) - allowed:
                    raise ValueError("Unknown query field")
                with lock:
                    result = state["engine"].query(**payload)
                    if answerer:
                        from answering import answer_query
                        result = answer_query(result,answerer)
                    return self.send_json(result)
            except (ValueError, KeyError, TypeError, UnicodeError) as e:
                return self.send_json({"error": str(e)}, 400)
            except Exception:
                return self.send_json({"error": "Internal error. See local server log."}, 500)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "synthetic.json")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--vector-model", default=None)
    parser.add_argument("--qa-model", default=None)
    args = parser.parse_args()
    server = create_server(args.data, args.port, args.vector_model, args.qa_model)
    print(f"Open http://127.0.0.1:{server.server_port}  |  data={args.data.name}  |  Ctrl+C to stop", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
