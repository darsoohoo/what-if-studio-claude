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
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs, quote

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "output"
TRASH = OUTPUT / "trash"
STATE_FILE = HERE / "review-notes.json"
PAGE_FILE = HERE / "review.html"
PRODUCE_PAGE = HERE / "produce.html"
SPEND_PAGE = HERE / "spend.html"
PRODUCE_DIR = HERE / "produce"
DOWNLOADS = Path.home() / "Downloads"
PORT = 8765

_lock = threading.Lock()
_render = {"proc": None, "log": HERE / "produce-render.log", "label": ""}

# The pipeline itself, imported for prompt building and voice listing.
import make_videos as mv


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


TEXT_AI = "https://text.pollinations.ai/"
OPENAI_API = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"


def openai_key():
    """Read the OpenAI key from OPENAI_API_KEY or pipeline/openai_key.txt."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    f = HERE / "openai_key.txt"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    return None


# Per-beat word budget for each runtime the app offers. The video is exactly
# as long as the narration, so the writer - not the runtime label - controls
# length. ~2.6 words/second of comfortable TTS narration.
RUNTIME_BEAT_WORDS = {
    30: ("12-20", "Keep it tight - every word earns its place."),
    60: ("15-30", "Brisk standard pace."),
    90: ("30-45", "Give each beat one extra concrete detail or example - let the twist breathe."),
    180: ("55-75", "Expand each beat with an example, a vivid aside, and one number or real fact."),
}


def draft_prompt(title, category, runtime=60):
    words, pace = RUNTIME_BEAT_WORDS.get(runtime, RUNTIME_BEAT_WORDS[60])
    return (
        'You write scripts for short-form "What if?" videos (TikTok explainer style). '
        f'For the question "{title}" (category: {category}), reply with ONLY minified JSON, '
        'no markdown fences, exactly this shape: '
        '{"premise":"...","beats":["...","...","...","...","..."],"tags":["...","...","..."],"emoji":"..."} '
        "Rules: premise = 2-3 vivid sentences setting up why this is fascinating. "
        f"beats = exactly 5 spoken-narration beats, {words} words each, no stage directions: "
        f"({pace}) "
        "1 the setup, 2 the immediate consequence, 3 the ripple effect nobody predicts, "
        "4 the twist or surprising real fact, 5 a payoff line that reframes the question. "
        "IMPORTANT: write beats as concrete HUMAN scenes someone could reenact on camera - "
        "show a specific person doing, holding, or reacting to something ('you reach for...', "
        "'a commuter drags...', 'a kid stares at...') in at least 4 of the 5 beats. "
        "Anchor in real facts where possible, clearly speculative in tone, punchy. "
        "tags = 3-5 lowercase topic words. emoji = one fitting emoji."
    )


def parse_draft(raw, engine):
    """Validate a raw model reply into the {premise, beats, tags, emoji} contract."""
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("no JSON in AI response")
    data = json.loads(raw[start:end + 1])
    beats = [str(b).strip() for b in (data.get("beats") or []) if str(b).strip()][:5]
    if not data.get("premise") or len(beats) < 3:
        raise RuntimeError("AI draft was incomplete - try again")
    return {
        "premise": str(data["premise"]).strip(),
        "beats": beats,
        "tags": [str(t).strip() for t in (data.get("tags") or []) if str(t).strip()][:5],
        "emoji": str(data.get("emoji") or "").strip()[:4],
        "engine": engine,
    }


def ai_draft_openai(title, category, key, runtime=60):
    """Draft via the OpenAI API (fast, no rate-limit queue; needs credits)."""
    body = json.dumps({
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": draft_prompt(title, category, runtime)}],
        "response_format": {"type": "json_object"},
        "temperature": 0.9,
        # Longer runtimes need room: 5 beats x up to ~75 words plus premise/tags.
        "max_tokens": 600 if runtime <= 60 else (900 if runtime <= 90 else 1500),
    }).encode("utf-8")
    req = urllib.request.Request(OPENAI_API, data=body, method="POST", headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "WhatIfStudio-review/1.0",
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        reply = json.loads(resp.read().decode("utf-8", "replace"))
    mv.record_spend("openai", "AI draft", mv.openai_usage_cost(reply),
                    OPENAI_MODEL, title[:60], estimated=True)
    raw = reply["choices"][0]["message"]["content"]
    return parse_draft(raw, "openai")


def ai_draft_pollinations(title, category, runtime=60):
    """Draft via the free Pollinations text API. Runs server-side because the
    API blocks direct browser requests (Turnstile) but allows plain server calls."""
    raw = None
    for attempt in range(3):
        url = TEXT_AI + quote(draft_prompt(title, category, runtime)) + f"?seed={int(time.time())}"
        req = urllib.request.Request(url, headers={"User-Agent": "WhatIfStudio-review/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read().decode("utf-8", "replace")
            break
        except urllib.error.HTTPError as exc:
            # The free tier rate-limits (~1 request / 15s) - wait and retry.
            if exc.code == 429 and attempt < 2:
                time.sleep(18)
                continue
            raise
    if raw is None:
        raise RuntimeError("the free writing service is busy - try again in a minute")
    return parse_draft(raw, "pollinations")


def ai_draft(title, category, runtime=60):
    """Draft premise/beats/tags/emoji for a scenario title, scaled to the
    selected runtime. Prefers the OpenAI API when a key is configured; falls
    back to the free Pollinations API otherwise (or if the OpenAI call fails)."""
    key = openai_key()
    if key:
        try:
            return ai_draft_openai(title, category, key, runtime)
        except Exception as exc:
            print(f"OpenAI draft failed ({exc}); falling back to the free writer")
    return ai_draft_pollinations(title, category, runtime)


# ---------------- produce (premium clip workflow) ----------------


def produce_dir(key):
    safe = re.sub(r"[^a-zA-Z0-9_-]", "-", str(key))[:80] or "clips"
    d = PRODUCE_DIR / safe
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_queues():
    """Queue exports in the pipeline folder, newest first."""
    out = []
    for f in sorted(HERE.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.name == "review-notes.json":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        items = data.get("items") if isinstance(data, dict) else None
        if not items:
            continue
        out.append({
            "file": f.name,
            "items": [{
                "slot": it.get("slot"),
                "title": (it.get("package") or {}).get("title", "untitled"),
                "scenarioId": (it.get("package") or {}).get("scenarioId", ""),
            } for it in items if it.get("package")],
        })
    return out


def load_package(queue_file, slot):
    name = safe_name(queue_file)
    path = (HERE / name) if name else None
    if not path or not path.is_file():
        raise RuntimeError("queue file not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    for it in data.get("items", []):
        if it.get("slot") == slot and it.get("package"):
            return it["package"]
    raise RuntimeError(f"slot {slot} not in {name}")


def staging_key(queue_file, slot, pkg):
    return f"{slot:02d}-{pkg.get('scenarioId', 'clips')}"


def staged_list(d):
    # mtime rides along as a cache-buster: swapping clips renames files, so a
    # position's URL keeps serving the browser's cached video without it.
    return [{"name": f.name, "size_mb": round(f.stat().st_size / 1e6, 2),
             "mtime": int(f.stat().st_mtime * 1000)}
            for f in sorted(d.glob("*.mp4"))]


def renumber(d):
    files = sorted(d.glob("*.mp4"))
    for i, f in enumerate(files):
        f.rename(d / f"zztmp_{i:02d}.mp4")
    for i, f in enumerate(sorted(d.glob("zztmp_*.mp4"))):
        f.rename(d / f"{i + 1:02d}.mp4")


def beat_prompts(pkg):
    segments = mv.narration_segments(pkg, 0)
    return [mv.ai_prompt_for_segment(pkg, i, len(segments), mv.VIDEO_MOTION_SUFFIX)
            for i in range(len(segments))]


def spend_summary():
    """Totals + breakdowns from the pipeline's spend ledger."""
    try:
        entries = json.loads(mv.SPEND_LEDGER.read_text(encoding="utf-8"))
        if not isinstance(entries, list):
            entries = []
    except Exception:
        entries = []
    today = time.strftime("%Y-%m-%d")
    month = time.strftime("%Y-%m")
    total = today_sum = month_sum = est_sum = 0.0
    by_service, by_scenario = {}, {}
    for e in entries:
        p = float(e.get("price_usd") or 0)
        ts = str(e.get("ts", ""))
        total += p
        if ts.startswith(today):
            today_sum += p
        if ts.startswith(month):
            month_sum += p
        if e.get("estimated"):
            est_sum += p
        svc = e.get("service", "?")
        by_service[svc] = by_service.get(svc, 0.0) + p
        sc = e.get("scenario") or "(none)"
        by_scenario[sc] = by_scenario.get(sc, 0.0) + p
    top_scenarios = sorted(by_scenario.items(), key=lambda kv: -kv[1])[:12]
    return {
        "total": round(total, 4),
        "today": round(today_sum, 4),
        "month": round(month_sum, 4),
        "estimated_portion": round(est_sum, 4),
        "by_service": {k: round(v, 4) for k, v in sorted(by_service.items(), key=lambda kv: -kv[1])},
        "by_scenario": [{"scenario": k, "usd": round(v, 4)} for k, v in top_scenarios],
        "entries": list(reversed(entries[-80:])),
        "count": len(entries),
    }


def observed_prices():
    """Average billed price per tryinfer job, learned from the spend ledger:
    {"video": {model: usd_per_clip}, "image": {model: usd_per_image}}. The API
    publishes no rates, so the user's own renders are the source of truth."""
    try:
        entries = json.loads(mv.SPEND_LEDGER.read_text(encoding="utf-8"))
        if not isinstance(entries, list):
            entries = []
    except Exception:
        entries = []
    sums, counts = {"video": {}, "image": {}}, {"video": {}, "image": {}}
    for e in entries:
        if e.get("service") != "tryinfer":
            continue
        kind = {"video clip": "video", "image": "image"}.get(e.get("kind"))
        model = e.get("model")
        price = float(e.get("price_usd") or 0)
        if not kind or not model or price <= 0:
            continue
        sums[kind][model] = sums[kind].get(model, 0.0) + price
        counts[kind][model] = counts[kind].get(model, 0) + 1
    return {k: {m: round(sums[k][m] / counts[k][m], 4) for m in sums[k]} for k in sums}


_catalog_cache = {"models": None}


def infer_catalog():
    """The tryinfer model catalog, fetched once per server run."""
    if _catalog_cache["models"] is None:
        models = []
        key = mv.infer_api_key()
        if key:
            try:
                models = mv.infer_list_models(key)
            except Exception:
                models = []
        _catalog_cache["models"] = models
    return _catalog_cache["models"]


def image_models():
    return sorted(m["model_id"] for m in infer_catalog()
                  if m.get("capability") == "text-to-image")


def video_models():
    return sorted(m["model_id"] for m in infer_catalog()
                  if m.get("capability") == "image-to-video")


def render_running():
    return _render["proc"] is not None and _render["proc"].poll() is None


def start_render(queue_file, slot, staging, opts):
    if render_running():
        raise RuntimeError("a render is already running - wait for it to finish")
    cmd = [sys.executable, "make_videos.py", queue_file, "--slots", str(slot),
           "--backgrounds", str(staging), "--out", "output"]
    if opts.get("infer"):
        cmd.append("--infer")
        model = re.sub(r"[^a-zA-Z0-9._-]", "", str(opts.get("infer_model") or ""))[:60]
        if model:
            cmd += ["--infer-model", model]
    elif opts.get("infer_images"):
        model = re.sub(r"[^a-zA-Z0-9._-]", "", str(opts["infer_images"]))[:60]
        if model:
            cmd += ["--infer-images", model]
        style = str(opts.get("ai_style") or "").strip()
        if model and style in mv.AI_STYLES:
            cmd += ["--ai-style", style]
    elif opts.get("ai_visuals"):
        cmd.append("--ai-visuals")
        style = str(opts.get("ai_style") or "").strip()
        if style in mv.AI_STYLES:
            cmd += ["--ai-style", style]
    if opts.get("elevenlabs"):
        cmd.append("--elevenlabs")
    if opts.get("charts"):
        cmd.append("--charts")
    try:
        vol = float(opts.get("clip_audio") or 0)
    except (TypeError, ValueError):
        vol = 0
    if vol > 0:
        cmd += ["--clip-audio", str(min(vol, 1.0))]
    voice = str(opts.get("voice") or "").strip()
    if voice and voice.lower() != "auto":
        cmd += ["--el-voice", voice]
    log = open(_render["log"], "w", encoding="utf-8")
    _render["proc"] = subprocess.Popen(cmd, cwd=HERE, stdout=log, stderr=subprocess.STDOUT)
    _render["label"] = f"slot {slot} from {queue_file}"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # keep the console quiet

    # ---------------- helpers ----------------

    def send_json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        # The static app (file:// or localhost) calls /api/draft cross-origin.
        self.send_header("Access-Control-Allow-Origin", "*")
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

    def send_page(self, page_file):
        body = page_file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_page(PAGE_FILE)
            return
        if self.path.split("?")[0] == "/produce":
            self.send_page(PRODUCE_PAGE)
            return
        if self.path.split("?")[0] == "/spend":
            self.send_page(SPEND_PAGE)
            return
        if self.path == "/api/spend":
            self.send_json(spend_summary())
            return
        if self.path.split("?")[0] in ("/help", "/help.html"):
            help_page = HERE.parent / "help.html"
            if help_page.is_file():
                self.send_page(help_page)
            else:
                self.send_json({"error": "help.html not found"}, 404)
            return
        if self.path == "/api/videos":
            self.send_json(list_videos())
            return
        if self.path == "/api/produce/queues":
            self.send_json(list_queues())
            return
        if self.path.startswith("/api/produce/info"):
            q = parse_qs(urlparse(self.path).query)
            try:
                queue = (q.get("queue") or [""])[0]
                slot = int((q.get("slot") or ["0"])[0])
                pkg = load_package(queue, slot)
                d = produce_dir(staging_key(queue, slot, pkg))
                voices, auto_voice = [], None
                key = mv.elevenlabs_key()
                if key:
                    try:
                        voices = mv.elevenlabs_voice_meta(key)
                        auto_voice = mv.auto_voice_name(pkg.get("voice", ""),
                                                        [v["name"] for v in voices])
                    except Exception:
                        voices = []
                self.send_json({
                    "image_models": image_models(),
                    "video_models": video_models(),
                    "observed_prices": observed_prices(),
                    "title": pkg.get("title"),
                    "dir": d.name,
                    "prompts": beat_prompts(pkg),
                    "staged": staged_list(d),
                    "voices": voices,
                    "auto_voice": auto_voice,
                    "elevenlabs": bool(key),
                    "infer": bool(mv.infer_api_key()),
                    "rendering": render_running(),
                })
            except Exception as exc:
                self.send_json({"error": str(exc)}, 400)
            return
        if self.path == "/api/produce/render-status":
            log_tail = ""
            try:
                log_tail = _render["log"].read_text(encoding="utf-8", errors="replace")[-2500:]
            except Exception:
                pass
            done_ok = (_render["proc"] is not None and _render["proc"].poll() == 0)
            self.send_json({"running": render_running(), "label": _render["label"],
                            "ok": done_ok, "log": log_tail})
            return
        if self.path.startswith("/produce-files/"):
            parts = self.path.split("?")[0][len("/produce-files/"):].split("/")
            if len(parts) == 2:
                dname, fname = safe_name(parts[0]), safe_name(parts[1])
                path = (PRODUCE_DIR / dname / fname) if dname and fname else None
                if path and path.is_file():
                    self.send_file(path, "video/mp4")
                    return
            self.send_json({"error": "not found"}, 404)
            return
        if self.path.startswith("/api/draft"):
            q = parse_qs(urlparse(self.path).query)
            title = (q.get("title") or [""])[0].strip()[:200]
            category = (q.get("category") or ["Speculative"])[0].strip()[:40]
            try:
                runtime = int((q.get("runtime") or ["60"])[0])
            except ValueError:
                runtime = 60
            if not title:
                self.send_json({"error": "missing title"}, 400)
                return
            try:
                self.send_json(ai_draft(title, category, runtime))
            except Exception as exc:
                self.send_json({"error": str(exc)}, 502)
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
        # Raw-body clip upload (drag & drop) - not JSON.
        if self.path.startswith("/api/produce/upload"):
            q = parse_qs(urlparse(self.path).query)
            dname = safe_name((q.get("dir") or [""])[0])
            if not dname:
                self.send_json({"error": "bad dir"}, 400)
                return
            d = produce_dir(dname)
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length <= 0 or length > 500_000_000:
                self.send_json({"error": "bad size"}, 400)
                return
            with _lock:
                index = len(list(d.glob("*.mp4"))) + 1
                dest = d / f"{index:02d}.mp4"
                with open(dest, "wb") as out:
                    remaining = length
                    while remaining > 0:
                        chunk = self.rfile.read(min(65536, remaining))
                        if not chunk:
                            break
                        out.write(chunk)
                        remaining -= len(chunk)
            self.send_json({"ok": True, "staged": staged_list(d)})
            return

        try:
            data = self.read_body()
        except Exception:
            self.send_json({"error": "bad json"}, 400)
            return

        if self.path == "/api/produce/import":
            dname = safe_name(str(data.get("dir", "")))
            count = max(1, min(int(data.get("count") or 1), 20))
            if not dname:
                self.send_json({"error": "bad dir"}, 400)
                return
            d = produce_dir(dname)
            recent = sorted(
                (f for f in DOWNLOADS.glob("*.mp4") if f.is_file()),
                key=lambda f: f.stat().st_mtime, reverse=True)[:count]
            if not recent:
                self.send_json({"error": "no .mp4 files found in your Downloads folder"}, 404)
                return
            with _lock:
                for old in d.glob("*.mp4"):
                    old.unlink()
                for i, src in enumerate(reversed(recent)):   # oldest first = generation order
                    shutil.copy2(src, d / f"{i + 1:02d}.mp4")
            self.send_json({"ok": True, "imported": [f.name for f in reversed(recent)],
                            "staged": staged_list(d)})
            return

        if self.path in ("/api/produce/remove", "/api/produce/clear", "/api/produce/swap"):
            dname = safe_name(str(data.get("dir", "")))
            if not dname or not (PRODUCE_DIR / dname).is_dir():
                self.send_json({"error": "bad dir"}, 400)
                return
            d = PRODUCE_DIR / dname
            with _lock:
                if self.path.endswith("clear"):
                    for f in d.glob("*.mp4"):
                        f.unlink()
                elif self.path.endswith("remove"):
                    name = safe_name(str(data.get("name", "")))
                    target = (d / name) if name else None
                    if target and target.is_file():
                        target.unlink()
                    renumber(d)
                else:  # swap
                    a, b = safe_name(str(data.get("a", ""))), safe_name(str(data.get("b", "")))
                    fa, fb = (d / a) if a else None, (d / b) if b else None
                    if fa and fb and fa.is_file() and fb.is_file():
                        tmp = d / "zzswap.mp4"
                        fa.rename(tmp)
                        fb.rename(d / a)
                        tmp.rename(d / b)
            self.send_json({"ok": True, "staged": staged_list(d)})
            return

        if self.path == "/api/produce/render":
            try:
                queue = safe_name(str(data.get("queue", "")))
                slot = int(data.get("slot") or 0)
                pkg = load_package(queue, slot)
                d = produce_dir(staging_key(queue, slot, pkg))
                # AI modes generate their own visuals - staged clips aren't needed.
                if (not data.get("infer") and not data.get("ai_visuals")
                        and not data.get("infer_images") and not list(d.glob("*.mp4"))):
                    raise RuntimeError("no clips staged - import or drop clips first")
                start_render(queue, slot, d, data)
                self.send_json({"ok": True})
            except Exception as exc:
                self.send_json({"error": str(exc)}, 400)
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
