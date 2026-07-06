#!/usr/bin/env python3
"""
What If Studio - video review dashboard.

A tiny LOCAL-ONLY server (binds 127.0.0.1, Python stdlib, no dependencies)
for reviewing rendered videos in output/: watch them, reorder the posting
queue, jot notes, read post kits, and remove videos (moved to output/trash,
never hard-deleted).

Start it:   double-click review.bat   (or: python review.py --open)
Then open:  http://127.0.0.1:8765
Stop it:    close the console window (or Ctrl+C).

Notes and ordering persist in review-notes.json next to this script.
"""

import argparse
import json
import re
import shutil
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "output"
TRASH = OUTPUT / "trash"
STATE_FILE = HERE / "review-notes.json"
PAGE_FILE = HERE / "review.html"
PORT = 8765

_lock = threading.Lock()


def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"order": [], "notes": {}}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def safe_name(name):
    """Only bare filenames that exist in output/ - no path tricks."""
    name = unquote(name)
    if not name or any(c in name for c in ("/", "\\", "..", ":")):
        return None
    return name


def video_title(stem):
    """Prefer the title from the post kit; fall back to a prettified slug."""
    kit = OUTPUT / f"{stem}-post.txt"
    try:
        first = kit.read_text(encoding="utf-8").splitlines()[0]
        if first.startswith("POST KIT - "):
            return first[len("POST KIT - "):].strip()
    except Exception:
        pass
    return re.sub(r"^\d+-", "", stem).replace("-", " ").capitalize()


def list_videos():
    state = load_state()
    vids = {}
    for f in sorted(OUTPUT.glob("*.mp4")):
        stem = f.stem
        vids[f.name] = {
            "name": f.name,
            "title": video_title(stem),
            "size_mb": round(f.stat().st_size / 1e6, 1),
            "mtime": int(f.stat().st_mtime),
            "thumb": f"{stem}-thumb.jpg" if (OUTPUT / f"{stem}-thumb.jpg").exists() else None,
            "post": (OUTPUT / f"{stem}-post.txt").read_text(encoding="utf-8")
                    if (OUTPUT / f"{stem}-post.txt").exists() else "",
            "note": state["notes"].get(f.name, ""),
        }
    ordered = [vids.pop(n) for n in state["order"] if n in vids]
    ordered += sorted(vids.values(), key=lambda v: v["mtime"])   # new files last
    return ordered


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # keep the console quiet

    # ---------------- helpers ----------------

    def send_json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        return json.loads(self.rfile.read(length) or b"{}")

    def send_file(self, path, ctype):
        """Serve a file with HTTP Range support so <video> can seek."""
        size = path.stat().st_size
        start, end = 0, size - 1
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                if m.group(2):
                    end = min(int(m.group(2)), size - 1)
                elif m.group(1):
                    end = size - 1
        start = max(0, min(start, size - 1))
        end = max(start, min(end, size - 1))
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = f.read(min(65536, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (ConnectionAbortedError, BrokenPipeError):
                    return
                remaining -= len(chunk)

    # ---------------- routes ----------------

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = PAGE_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/videos":
            self.send_json(list_videos())
            return
        if self.path.startswith("/files/"):
            name = safe_name(self.path[len("/files/"):])
            path = (OUTPUT / name) if name else None
            if not path or not path.is_file():
                self.send_json({"error": "not found"}, 404)
                return
            ctype = "video/mp4" if path.suffix == ".mp4" else "image/jpeg"
            self.send_file(path, ctype)
            return
        self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        try:
            data = self.read_body()
        except Exception:
            self.send_json({"error": "bad json"}, 400)
            return

        with _lock:
            state = load_state()

            if self.path == "/api/order":
                order = data.get("order")
                if isinstance(order, list) and all(isinstance(n, str) for n in order):
                    state["order"] = order
                    save_state(state)
                    self.send_json({"ok": True})
                else:
                    self.send_json({"error": "order must be a list of names"}, 400)
                return

            if self.path == "/api/note":
                name = safe_name(data.get("name", ""))
                if name:
                    state["notes"][name] = str(data.get("text", ""))[:5000]
                    save_state(state)
                    self.send_json({"ok": True})
                else:
                    self.send_json({"error": "bad name"}, 400)
                return

            if self.path == "/api/delete":
                name = safe_name(data.get("name", ""))
                src = (OUTPUT / name) if name else None
                if not src or not src.is_file() or src.suffix != ".mp4":
                    self.send_json({"error": "not found"}, 404)
                    return
                TRASH.mkdir(parents=True, exist_ok=True)
                moved = []
                for sib in (src, OUTPUT / f"{src.stem}-thumb.jpg", OUTPUT / f"{src.stem}-post.txt"):
                    if sib.is_file():
                        shutil.move(str(sib), str(TRASH / sib.name))
                        moved.append(sib.name)
                state["order"] = [n for n in state["order"] if n != name]
                state["notes"].pop(name, None)
                save_state(state)
                self.send_json({"ok": True, "moved": moved})
                return

        self.send_json({"error": "not found"}, 404)


def main():
    parser = argparse.ArgumentParser(description="Local review dashboard for rendered videos.")
    parser.add_argument("--open", action="store_true", help="open the dashboard in your browser")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    OUTPUT.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"Review dashboard running at {url}  (local-only; Ctrl+C to stop)")
    if args.open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
