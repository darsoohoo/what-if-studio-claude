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
import base64
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
STUDIO = HERE.parent
STUDIO_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
}
OUTPUT = HERE / "output"
TRASH = OUTPUT / "trash"
STATE_FILE = HERE / "review-notes.json"
PAGE_FILE = HERE / "review.html"
PRODUCE_PAGE = HERE / "produce.html"
SPEND_PAGE = HERE / "spend.html"
RESULTS_PAGE = HERE / "results.html"
RESULTS_FILE = HERE / "results.json"
RESULT_PLATFORMS = ("TikTok", "YT Shorts", "Reels")
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


def load_results():
    """Manually logged per-platform performance numbers, keyed by video name."""
    try:
        return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_results(results):
    RESULTS_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")


def video_meta(stem):
    """Category/runtime/voice for one rendered video: the render's -meta.json
    sidecar when present, else a title-slug match against archived exports
    (covers videos rendered before the sidecar existed)."""
    try:
        return json.loads((OUTPUT / f"{stem}-meta.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    slug = re.sub(r"-v\d+$", "", re.sub(r"^\d+-", "", stem))
    files = list(EXPORTS_DIR.glob("*.json")) if EXPORTS_DIR.is_dir() else []
    for f in files:
        try:
            items = json.loads(f.read_text(encoding="utf-8")).get("items") or []
        except Exception:
            continue
        for it in items:
            pkg = it.get("package") or {}
            if mv.slugify(pkg.get("title", "")) == slug:
                return {"title": pkg.get("title", ""), "category": pkg.get("category", ""),
                        "runtime": pkg.get("runtime"), "voice": pkg.get("voice", ""),
                        "scenarioId": pkg.get("scenarioId", "")}
    return {}


def results_payload():
    """Posted videos joined with their render metadata and logged stats."""
    stats = load_results()
    out = []
    for v in list_videos():
        if not v.get("uploaded"):
            continue
        meta = video_meta(Path(v["name"]).stem)
        out.append({
            "name": v["name"], "title": v["title"], "thumb": v["thumb"],
            "uploaded": v["uploaded"],
            "category": meta.get("category") or "",
            "runtime": meta.get("runtime"), "voice": meta.get("voice") or "",
            # Renders before format tagging existed were all classic.
            "format": meta.get("format") or "classic",
            "mood": meta.get("mood") or "",
            "visuals": meta.get("visuals") or "",
            "stats": stats.get(v["name"], {}),
        })
    return {"videos": out, "platforms": list(RESULT_PLATFORMS)}


def safe_name(name):
    """Only bare filenames that exist in output/ - no path tricks."""
    name = unquote(name)
    if not name or any(c in name for c in ("/", "\\", "..", ":")):
        return None
    return name


def studio_file(url_path):
    """Map /studio/... to a static file in the project root."""
    path = url_path.split("?")[0]
    if path in ("/studio", "/studio/"):
        rel = "index.html"
    elif path.startswith("/studio/"):
        rel = unquote(path[len("/studio/"):])
    else:
        return None
    if not rel or rel.startswith(("/", "\\")) or ".." in Path(rel).parts:
        return None
    target = (STUDIO / rel).resolve()
    try:
        target.relative_to(STUDIO.resolve())
    except ValueError:
        return None
    return target if target.is_file() else None


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
            # epoch seconds when the user marked it posted, or None
            "uploaded": state.get("uploaded", {}).get(f.name),
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


def openai_admin_key():
    """An OpenAI ADMIN key (platform.openai.com -> settings -> Admin keys)
    unlocks the official Costs API. Regular secret keys get a 403 on every
    billing endpoint, and the remaining-balance number is browser-only."""
    key = os.environ.get("OPENAI_ADMIN_KEY", "").strip()
    if key:
        return key
    f = HERE / "openai_admin_key.txt"
    if f.exists():
        return f.read_text(encoding="utf-8").strip() or None
    return None


_openai_costs_cache = {"ts": 0.0, "data": None}


def openai_month_costs():
    """Month-to-date OpenAI cost in real billed dollars via the Costs API.
    Needs an admin key; results cache for 10 minutes so the Spend page's
    polling never hammers OpenAI."""
    key = openai_admin_key()
    if not key:
        return {"available": False, "reason": "no_admin_key"}
    now = time.time()
    if _openai_costs_cache["data"] is not None and now - _openai_costs_cache["ts"] < 600:
        return _openai_costs_cache["data"]
    try:
        start = int(time.mktime(time.strptime(time.strftime("%Y-%m-01"), "%Y-%m-%d")))
        total, page = 0.0, None
        for _ in range(6):   # paginated: 6 pages x 31 buckets is plenty for a month
            url = f"https://api.openai.com/v1/organization/costs?start_time={start}&limit=31"
            if page:
                url += f"&page={quote(page)}"
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {key}",
                "User-Agent": "WhatIfStudio-review/1.0",
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                reply = json.loads(resp.read().decode("utf-8", "replace"))
            for bucket in reply.get("data", []):
                for r in bucket.get("results", []):
                    total += float((r.get("amount") or {}).get("value") or 0)
            if not reply.get("has_more"):
                break
            page = reply.get("next_page")
        data = {"available": True, "month_usd": round(total, 4)}
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:200]
        except Exception:
            pass
        # Not cached: the moment the user fixes the key, the next poll works.
        return {"available": False, "reason": f"OpenAI said HTTP {exc.code}",
                "detail": detail}
    except Exception as exc:
        return {"available": False, "reason": str(exc)[:200]}
    _openai_costs_cache.update(ts=now, data=data)
    return data


# Per-beat word budget for each runtime the app offers. The video is exactly
# as long as the narration, so the writer - not the runtime label - controls
# length. ~2.6 words/second of comfortable TTS narration.
RUNTIME_BEAT_WORDS = {
    30: ("12-20", "Keep it tight - every word earns its place."),
    60: ("15-30", "Brisk standard pace."),
    90: ("30-45", "Give each beat one extra concrete detail or example - let the twist breathe."),
    180: ("55-75", "Expand each beat with an example, a vivid aside, and one number or real fact."),
}


def beat_word_budget(runtime, beats=5):
    """Per-beat word range for `beats` beats. The table is calibrated for 5;
    more beats split the SAME total narration into shorter lines, so the
    video stays as long as the runtime label - the cuts just come faster."""
    words, pace = RUNTIME_BEAT_WORDS.get(runtime, RUNTIME_BEAT_WORDS[60])
    if beats != 5:
        lo, hi = (int(w) for w in words.split("-"))
        lo = max(6, round(lo * 5 / beats))
        hi = max(lo + 4, round(hi * 5 / beats))
        words = f"{lo}-{hi}"
    return words, pace


def draft_prompt(title, category, runtime=60, beats=5, idea=None, mood=None):
    words, pace = beat_word_budget(runtime, beats)
    shape = (
        'reply with ONLY minified JSON, no markdown fences, exactly this shape: '
        '{"premise":"...","beats":[' + ",".join(['"..."'] * beats) + '],'
        '"tags":["...","...","..."],"emoji":"...",'
        '"cast":[{"name":"...","look":"..."}]} '
        "cast = the story's recurring characters (0-3, empty list if none): a short "
        "first name plus look, a 6-12 word visual description (age, build, hair, one "
        "signature clothing item) that stays IDENTICAL every time they're on screen. "
        "Refer to them by these names in the beats. "
        # The creator's own summary/details ground the whole draft; an
        # explicit 🎭 mood flavors the register on top of the category's own.
        # (MOODS is defined later in the module - resolved at call time.)
        + ('Build the whole thing from these details the creator supplied - keep every '
           f'named fact, person, and place: "{idea}" ' if idea else "")
        + (f"Tell it in a {MOODS[mood]} voice. " if mood and mood in MOODS else "")
        + (TRAILER_ONLY_RULE if mood == "trailer"
           else TRAILER_DIALOGUE_RULE if mood == "trailer-vo" else "")
    )
    if category == "Scary Story":
        # Narrative horror in the modern social-thriller register (the
        # Get Out / Twilight Zone school): the scare hides inside something
        # human, and the reveal reframes everything that came before.
        return (
            "You write scripts for short-form scary-story videos (TikTok horror narration: "
            "true-feeling, first-person or documentary tone, dread over gore) in the register "
            "of modern social-thriller horror: an ordinary person in a familiar world notices "
            "one quietly wrong detail, and the truth underneath says something real about "
            "people. "
            f'For the story "{title}", ' + shape +
            "Rules: premise = 2-3 sentences setting the scene and hinting at what's wrong. "
            f"beats = exactly {beats} spoken story beats, {words} words each, no stage directions: "
            f"({pace}) "
            + ("1 the ordinary setup with one detail slightly off, 2 the wrong detail becomes "
               "impossible to unsee, 3 the point of no return, 4 the reveal that RECONTEXTUALIZES "
               "everything before it - the horror was hiding in plain sight the whole time, "
               "5 a final line with a double meaning that lingers after the video ends. "
               if beats == 5 else
               f"1 the ordinary setup with one detail slightly off, 2-{beats - 2} the escalation - "
               "the wrong detail becomes impossible to unsee, then the point of no return, each "
               f"beat one concrete step deeper, {beats - 1} the reveal that RECONTEXTUALIZES "
               "everything before it - the horror was hiding in plain sight the whole time, "
               f"{beats} a final line with a double meaning that lingers after the video ends. ")
            + "Present tense, concrete sensory details (sounds, timestamps, textures), a specific "
            "person doing something in every beat. Root the fear in something human - grief, "
            "guilt, conformity, being watched, needing to belong, who gets believed, or a life "
            "that turns out to be curated for you - shown, never preached. Too-perfect places "
            "(planned suburbs, company towns, wellness communities, lives staged like showrooms) "
            "are welcome sources of dread. Fictional but grounded - no real victims, no gore, no "
            "jump-scare cliches. "
            "tags = 3-5 lowercase topic words. emoji = one fitting emoji."
        )
    if category == "True History":
        # Real events told documentary-style - accuracy over drama.
        return (
            "You write scripts for short-form true-history videos (TikTok documentary "
            "narration: vivid, punchy, but factually accurate). "
            f'For the real event or story "{title}", ' + shape +
            "Rules: premise = 2-3 sentences placing the event and why it sounds unbelievable. "
            f"beats = exactly {beats} spoken story beats, {words} words each, no stage directions: "
            f"({pace}) "
            + ("1 drop into the scene, 2 how it started, 3 the escalation, "
               "4 the twist or best-documented detail, 5 a payoff connecting it to today. "
               if beats == 5 else
               f"1 drop into the scene, 2 how it started, 3-{beats - 2} the escalation told "
               f"step by documented step, {beats - 1} the twist or best-documented detail, "
               f"{beats} a payoff connecting it to today. ")
            + "EVERY fact must be real and verifiable - dates, names, numbers. If a detail is "
            "debated or legend, say so in the narration itself ('accounts claim...', "
            "'historians still argue...'). Never invent quotes, statistics, or people. "
            "Show a specific person doing something concrete in most beats. "
            "tags = 3-5 lowercase topic words. emoji = one fitting emoji."
        )
    return (
        'You write scripts for short-form "What if?" videos (TikTok explainer style). '
        f'For the question "{title}" (category: {category}), ' + shape +
        "Rules: premise = 2-3 vivid sentences setting up why this is fascinating. "
        f"beats = exactly {beats} spoken-narration beats, {words} words each, no stage directions: "
        f"({pace}) "
        + ("1 the setup, 2 the immediate consequence, 3 the ripple effect nobody predicts, "
           "4 the twist or surprising real fact, 5 a payoff line that reframes the question. "
           if beats == 5 else
           f"1 the setup, 2 the immediate consequence, 3-{beats - 2} the ripple effects nobody "
           f"predicts, each beat a different corner of life, {beats - 1} the twist or surprising "
           f"real fact, {beats} a payoff line that reframes the question. ")
        + "IMPORTANT: write beats as concrete HUMAN scenes someone could reenact on camera - "
        "show a specific person doing, holding, or reacting to something ('you reach for...', "
        "'a commuter drags...', 'a kid stares at...') in at least "
        f"{beats - 1} of the {beats} beats. "
        "Anchor in real facts where possible, clearly speculative in tone, punchy. "
        "tags = 3-5 lowercase topic words. emoji = one fitting emoji."
    )


def parse_cast(raw_cast):
    """Clean an AI-written cast list into [{"name", "look"}] (max 4)."""
    cast = []
    for c in (raw_cast or [])[:4]:
        if not isinstance(c, dict):
            continue
        name = re.sub(r"\s+", " ", str(c.get("name", ""))).strip(" \"'[]")[:30]
        look = re.sub(r"\s+", " ", str(c.get("look", ""))).strip(" \"'")[:120]
        if name and look:
            cast.append({"name": name, "look": look})
    return cast


def parse_draft(raw, engine, want=5):
    """Validate a raw model reply into the {premise, beats, tags, emoji, cast} contract."""
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("no JSON in AI response")
    data = json.loads(raw[start:end + 1])
    beats = [str(b).strip() for b in (data.get("beats") or []) if str(b).strip()][:want]
    # A couple short is livable at high counts; below that the arc is broken.
    if not data.get("premise") or len(beats) < max(3, want - 2):
        raise RuntimeError("AI draft was incomplete - try again")
    return {
        "premise": str(data["premise"]).strip(),
        "beats": beats,
        "tags": [str(t).strip() for t in (data.get("tags") or []) if str(t).strip()][:5],
        "emoji": str(data.get("emoji") or "").strip()[:4],
        "cast": parse_cast(data.get("cast")),
        "engine": engine,
    }


def ai_draft_openai(title, category, key, runtime=60, beats=5, idea=None, mood=None):
    """Draft via the OpenAI API (fast, no rate-limit queue; needs credits)."""
    body = json.dumps({
        "model": OPENAI_MODEL,
        "messages": [{"role": "user",
                      "content": draft_prompt(title, category, runtime, beats, idea, mood)}],
        "response_format": {"type": "json_object"},
        "temperature": 0.9,
        # Longer runtimes need room: beats x up to ~75 words plus premise/tags.
        # Extra beats keep the same total words but add JSON overhead per line.
        "max_tokens": (600 if runtime <= 60 else (900 if runtime <= 90 else 1500))
                      + 40 * max(0, beats - 5),
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
    draft = parse_draft(raw, "openai", beats)
    draft["beats"] = finish_trailer_beats(draft["beats"], mood)
    return draft


def ai_draft_pollinations(title, category, runtime=60, beats=5, idea=None, mood=None):
    """Draft via the free Pollinations text API. Runs server-side because the
    API blocks direct browser requests (Turnstile) but allows plain server calls."""
    raw = None
    for attempt in range(3):
        url = (TEXT_AI + quote(draft_prompt(title, category, runtime, beats, idea, mood))
               + f"?seed={int(time.time())}")
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
    draft = parse_draft(raw, "pollinations", beats)
    draft["beats"] = finish_trailer_beats(draft["beats"], mood)
    return draft


def ai_draft(title, category, runtime=60, beats=5, idea=None, mood=None):
    """Draft premise/beats/tags/emoji for a scenario title, scaled to the
    selected runtime and beat count (clips = beats + hook + outro). `idea`
    grounds the draft in the creator's own summary/details; an explicit
    `mood` flavors the register. Prefers the OpenAI API when a key is
    configured; falls back to the free Pollinations API otherwise (or if
    the OpenAI call fails)."""
    key = openai_key()
    if key:
        try:
            return ai_draft_openai(title, category, key, runtime, beats, idea, mood)
        except Exception as exc:
            print(f"OpenAI draft failed ({exc}); falling back to the free writer")
    return ai_draft_pollinations(title, category, runtime, beats, idea, mood)


# ---------------- draft batches ----------------
# While the dashboard is running, draft ready-to-produce packages - daily
# for kinds flagged "daily" (after MORNING_HOUR), or on demand from the
# Produce page. Drafting ONLY - nothing is rendered, billed to tryinfer,
# or posted by itself. State in pipeline/morning-log.json (gitignored).

MORNING_HOUR = 6
MORNING_LOG = HERE / "morning-log.json"
_morning_lock = threading.Lock()

BATCHES = {
    "scary": {
        "label": "scary stories", "daily": True, "count": 3, "runtime": 90,
        "category": "Scary Story", "prefix": "morning",
        "colors": {"from": "#120a16", "to": "#8a2431"},
        "pacing": "Room to breathe: let the dread land.",
        "safety": "Fictional scary story - dread over gore, no real victims depicted.",
        "outro": "Sit with that one for a second. Follow for more scary stories.",
        "extra_caption": "Wait for the last line.",
        "fallback_tag": "scary story",
    },
    "whatif": {
        "label": "realistic what-ifs", "daily": False, "count": 3, "runtime": 90,
        "category": "Speculative", "prefix": "whatif",
        "colors": {"from": "#2dbf8b", "to": "#3a6ea5"},
        "pacing": "Room to breathe: full beat structure with one extra detail per beat.",
        "safety": "Speculative thought experiment anchored in real facts.",
        "outro": "Sit with that one for a second. Follow for the next what-if.",
        "extra_caption": "The wildest part is the true part.",
        "fallback_tag": "thought experiment",
    },
}

# Offline fallback titles per kind if both writers are unreachable.
BATCH_SEEDS = {
    "scary": [
        "The carpool app matched her with a car that has no driver",
        "The window cleaner who waved from the 14th floor of a 12-story building",
        "The overnight ferry that docks twice",
        "The last voicemail says to stop looking for him",
        "The house sitter's list ends with a rule that is crossed out",
        "The elevator inspector who never signs floor nine",
        "The campsite log everyone signs on the way in but not out",
        "The subway announcement that names you",
        "The motel room phone that only dials room 8",
        "The snowplow driver who keeps clearing a road that leads nowhere",
        "The neighbor's porch light that blinks in patterns",
        "The night fisherman who reels in his own tackle box",
    ],
    "whatif": [
        "What if school started at noon?",
        "What if antibiotics stopped working next year?",
        "What if the internet went down for a whole month?",
        "What if every commute counted as paid work time?",
        "What if food labels showed the hours of work they cost?",
        "What if cities banned private cars for one year?",
        "What if your memories could be used in court?",
        "What if everyone could see how their taxes were spent, live?",
        "What if naps were a legal right at work?",
        "What if every product showed its true lifetime cost?",
    ],
}


def load_morning_log():
    try:
        log = json.loads(MORNING_LOG.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if "date" in log:
        # Pre-kinds format: the whole file was the scary batch.
        log = {"scary": {k: log[k] for k in ("date", "titles", "history") if k in log}}
    return log


def _ai_text(prompt, max_tokens=300):
    """One JSON completion: OpenAI when a key exists, else Pollinations."""
    key = openai_key()
    if key:
        body = json.dumps({
            "model": OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 1.0,
            "max_tokens": max_tokens,
        }).encode("utf-8")
        req = urllib.request.Request(OPENAI_API, data=body, method="POST", headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "WhatIfStudio-review/1.0",
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    url = TEXT_AI + quote(prompt) + f"?seed={int(time.time())}"
    req = urllib.request.Request(url, headers={"User-Agent": "WhatIfStudio-review/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8", "replace")


def batch_titles(kind, recent, count):
    """Fresh titles for one batch kind from the AI, avoiding recent repeats."""
    avoid = ("Avoid anything similar to these recent ones: " + "; ".join(recent[-30:]) + "."
             if recent else "")
    if kind == "whatif":
        prompt = (
            "You invent short-form 'What if?' video questions that are REALISTIC "
            "thought experiments: grounded in real science, economics, psychology, "
            "history, or everyday life, so the video can be built from real facts. "
            "Each one should feel like it could plausibly happen, nearly be true, or "
            "reveal something true about how the world works. Strictly NO monsters, "
            "magic, ghosts, or the supernatural. "
            f"Invent {count} questions of 5-12 words, each starting with 'What if', "
            "in the register of: 'What if money expired after 30 days?' or "
            "'What if school started at noon?'. "
            'Reply with ONLY minified JSON, exactly: {"titles":["...","..."]}. ' + avoid
        )
    else:
        prompt = (
            "You name short-form scary-story videos: narrative dread, real-feeling, "
            "no gore, never phrased as a 'what if' question. Favor the social-thriller "
            "register - a familiar everyday setting (a job, a family ritual, an app, a "
            "neighborhood) hiding one quietly wrong thing, where the scare could turn out "
            "to say something about people. Too-perfect places are welcome too: planned "
            "suburbs, company towns, wellness communities, lives that feel staged. "
            f"Invent {count} fresh, specific story premises as titles of 5-12 words, "
            "in the register of: 'The dive log that ends mid-sentence', "
            "'The new neighbors all wave with the wrong hand', or "
            "'The model home furnished with your childhood photos'. "
            'Reply with ONLY minified JSON, exactly: {"titles":["...","..."]}. ' + avoid
        )
    try:
        raw = _ai_text(prompt)
        start, end = raw.find("{"), raw.rfind("}")
        titles = [str(t).strip() for t in json.loads(raw[start:end + 1]).get("titles", [])
                  if str(t).strip()]
        seen = {r.lower() for r in recent}
        titles = [t for t in titles if t.lower() not in seen][:count]
        if titles:
            return titles
    except Exception as exc:
        print(f"{kind} batch: title generation failed ({exc}); using the seed list")
    seen = {r.lower() for r in recent}
    pool = [s for s in BATCH_SEEDS[kind] if s.lower() not in seen] or list(BATCH_SEEDS[kind])
    return pool[:count]


def scaffold_batch_package(conf, title, draft, runtime):
    """A full render-ready package from an AI draft (server-side sibling of
    the app's buildPackage, styled per kind conf - a BATCHES or IDEA_KINDS
    entry)."""
    first = draft["premise"].split(". ")[0].rstrip(".") + "."
    return {
        "scenarioId": f"{conf['prefix']}-" + mv.slugify(title)[:28],
        "title": title,
        "category": conf["category"],
        "colors": dict(conf["colors"]),
        "platform": "Any",
        "aspect": "9:16 vertical",
        "runtime": runtime,
        "runtimeLabel": "3 min" if runtime == 180 else f"{runtime}s",
        "pacingNote": conf["pacing"],
        "voice": "Calm Narrator",
        "direction": "Low, steady, confident. Let pauses do the work. Never rush the payoff line.",
        "premise": draft["premise"],
        "safety": conf["safety"],
        "tags": draft.get("tags") or [conf["fallback_tag"]],
        "hooks": [first],
        "beats": draft["beats"],
        "cast": draft.get("cast") or [],
        "outro": conf["outro"],
        "captions": [title, conf["extra_caption"]],
        "thumbnails": [" ".join(title.split()[:4]).upper()],
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def write_package_export(pkg, prefix, title):
    """Archive one drafted package as a one-item queue export; returns the
    dropdown-ready 'exports/<name>' path."""
    EXPORTS_DIR.mkdir(exist_ok=True)
    name = (f"whatifstudio-queue-{prefix}-{mv.slugify(title)[:40]}"
            f"-{time.strftime('%Y%m%d-%H%M%S')}.json")
    (EXPORTS_DIR / name).write_text(json.dumps({
        "app": "what-if-studio", "format": 1,
        "exportedAt": pkg["generatedAt"],
        "items": [{"slot": 1, "status": "planned", "notes": "", "package": pkg}],
    }, indent=2), encoding="utf-8")
    return f"exports/{name}"


# Kinds the 💡 draft-from-your-idea box offers: the two batch kinds plus
# True History (which has no daily batch of its own).
IDEA_KINDS = dict(BATCHES)
IDEA_KINDS["history"] = {
    "label": "true history", "runtime": 90,
    "category": "True History", "prefix": "idea",
    "colors": {"from": "#241a10", "to": "#8a6d2f"},
    "pacing": "Documentary pace: let the facts land.",
    "safety": "Real documented history - accuracy over drama, nothing invented.",
    "outro": "History keeps receipts. Follow for more true history.",
    "extra_caption": "The wildest part is documented.",
    "fallback_tag": "true history",
}


def title_from_idea(idea, category):
    """A short video title distilled from the creator's summary. Falls back
    to the idea's opening words if the writer is unreachable."""
    try:
        raw = _ai_text(
            f'You title short-form {category} videos. Distill this idea into one '
            f'title of 5-12 words - specific, no quotes, no "what if" unless the '
            f'idea is a what-if question: "{idea[:600]}". '
            'Reply with ONLY minified JSON, exactly: {"title":"..."}')
        start, end = raw.find("{"), raw.rfind("}")
        title = re.sub(r"\s+", " ", str(json.loads(raw[start:end + 1]).get("title", ""))).strip(" \"'")
        if 3 <= len(title.split()) <= 16:
            return title[:120]
    except Exception:
        pass
    return " ".join(idea.split()[:10])


def batch_run(kind="scary", force=False, beats=5):
    """Draft one kind's packages into exports/ (once per day unless forced).
    `beats` = spoken story beats per package; clips = beats + hook + outro."""
    conf = BATCHES[kind]
    with _morning_lock:
        log = load_morning_log()
        entry = log.get(kind, {})
        today = time.strftime("%Y-%m-%d")
        if entry.get("date") == today and not force:
            return {"kind": kind, "date": today, "made": [],
                    "titles": entry.get("titles", []), "already": True}
        recent = entry.get("history", [])
        made = []
        for title in batch_titles(kind, recent, conf["count"]):
            try:
                draft = ai_draft(title, conf["category"], conf["runtime"], beats)
                pkg = scaffold_batch_package(conf, title, draft, conf["runtime"])
                write_package_export(pkg, conf["prefix"], title)
                made.append(title)
            except Exception as exc:
                print(f"{kind} batch: '{title}' failed: {exc}")
        titles = (entry.get("titles", []) if entry.get("date") == today else []) + made
        if made:
            log[kind] = {"date": today, "titles": titles, "history": (recent + made)[-60:]}
            MORNING_LOG.write_text(json.dumps(log, indent=2), encoding="utf-8")
        return {"kind": kind, "date": today, "made": made, "titles": titles, "already": False}


def morning_loop():
    """Background timer: daily-flagged batches fire once a day after MORNING_HOUR."""
    while True:
        try:
            if time.localtime().tm_hour >= MORNING_HOUR:
                log = load_morning_log()
                today = time.strftime("%Y-%m-%d")
                for kind, conf in BATCHES.items():
                    if conf["daily"] and log.get(kind, {}).get("date") != today:
                        res = batch_run(kind)
                        if res["made"]:
                            print(f"{kind} batch: drafted " + " | ".join(res["made"]))
        except Exception as exc:
            print(f"batch loop: {exc}")
        time.sleep(600)


# ---------------- in-app assistant chat ----------------

# The app executes ONLY these actions (see runAssistantAction in app.js) -
# nothing destructive is on the list, so a confused model can't wipe data.
CHAT_ACTIONS = """\
- select_scenario {"title": "..."} - open a library scenario by approximate title
- search {"query": "...", "category": "..."} - filter the library (category optional)
- set_options {"runtime": 30|60|90|180, "voice": "calm"|"hype"|"deadpan"} - either or both
- generate {} - build the package for the selected scenario and export it for render
- create_scenario {"title": "...", "category": "...", "render": true|false} - AI-draft a brand-new scenario into the library; what-if categories get a "What if ...?" question as the title, while the story categories (Scary Story, True History) take a plain narrative title; render=true also generates + exports it
- render_category {"category": "..."} - export EVERY scenario in one category as a single multi-slot render queue; the watcher renders them back-to-back
- export {"format": "txt"|"srt"|"json"} - export the generated package
- new_seed {} - spin the scenario seed generator for a fresh idea
- navigate {"page": "studio"|"videos"|"produce"|"results"|"spend"|"help"} - open another page
- check_renders {} - report render progress and the newest finished videos (works on every page)
- get_post_kit {"video": "newest" or an approximate title} - fetch a finished video's post kit: caption + per-platform hashtags, with a copy button (works on every page)
- mark_posted {"video": "newest" or an approximate title, "posted": true|false} - flag a finished video as posted (or not), same toggle as the Videos page (works on every page)"""

CHAT_APP_FACTS = """\
What If Studio makes short-form "What if?" videos (TikTok / YouTube Shorts / Reels, 9:16 vertical).
The app is a local static page: scenario library (10 categories - 8 "what if" ones plus two story categories that brand their own renders automatically: Scary Story, social-thriller narrative horror with eerie still-and-symmetrical visuals + a "follow for more scary stories" CTA + horror hashtags, and True History, real documented events with archival visuals + a "follow for more true history" CTA + history hashtags), package settings (runtime 30s/60s/90s/3min; voice Calm/High-Energy/Deadpan), and "Generate + Export for render" which downloads a queue .json. A watcher (started via Start-What-If-Studio.bat) picks that file up from Downloads and renders the full video: TTS voiceover, word-synced captions, per-beat visuals, music, thumbnail, and a post kit with per-platform hashtags. Posting is always manual.
Custom scenarios: the builder ("+ Create your own scenario") with an AI "Write it for me" draft, all editable, saved in the browser's local storage.
Draft batches: while the dashboard runs, it drafts 3 fresh 90s Scary Story packages daily after 6:00, and Produce has two on-demand buttons - 🌅 for 3 more scary scenarios, 💭 for 3 realistic what-ifs (grounded thought experiments from real facts, no monsters or magic); the Clips dropdown next to them picks 7 (default), 9, 12, or 15 clips per video (hook + beats + outro - more clips = faster cuts at the same length, reveal still on the second-to-last beat); everything lands in the Produce package dropdown with per-beat prompts ready to copy into tryinfer Studio. Drafting only - nothing renders or posts by itself.
Dashboard pages (this server, 127.0.0.1:8765): Videos (review renders), Produce (per-beat visuals, voices, re-render), Results (log posted videos' views/likes by hand; rollups by category AND by render format - Classic vs Ironic cheerful vs Movie trailer, with mood/visuals badges - show what's winning), Spend (API costs), Help.
Produce 🎯 Workflow picker (top of step 2): presets - Modern trailer / Narrated trailer / Ironic horror / Classic - set the mood, music checkboxes, and suggested clip count in one pick, and show a numbered 1-2-3 trail on the buttons to follow (script -> prompts -> render). Free-form = no guidance.
Produce per-beat references: attach an image and/or your own video to any beat; the radio picks which one the beat uses and it ALWAYS lands in the final video - image = the picture is that beat's visual with gentle motion (in AI-video mode it's animated as the clip's first frame instead), video = the clip plays as-is (never billed). A 🎭 Mood dropdown (Auto = category default, or Eerie, Funny, Sarcastic, Witty, Adventurous, Dramatic, Mysterious, Wholesome, Inspiring, Deadpan) steers two rewrite buttons: "Script from prompts" writes the whole spoken script fitted to the visual prompts, "Prompts from script" re-imagines every visual prompt from the spoken lines; both save with the old version kept in History. The same mood flavors every ✨ line rewrite, and an explicit (non-Auto) mood also restyles generated visuals at render time.
🎵 Ironic cheerful music (Render checkbox, or --ironic-music): a sincerely happy bed (music/ironic - 1950s swing, ragtime, elevator muzak; python get_music.py fetches them) that contradicts scary visuals, plays straight until the reveal beat, then tape-stops on its first word with a soft impact and resumes slowed + quiet. Any category, any visuals mode. With Mood on Auto it also renders generated visuals in Wholesome mood - smiling pictures, cheerful song, dark script - the full Jordan Peele contradiction in one click (an explicit mood overrides the look).
🎬 Movie-trailer feel (Render checkbox, or --trailer; excludes the ironic checkbox): for horror categories the soundtrack is a synthesized AHS-style dread bed (heartbeat pulse, detuned drone, metallic shrieks - nothing to license), other categories get an epic bed from music/trailer (--trailer-bed overrides); plus riser + impact on the reveal, extra breathing room between dialogue lines, slower narrator delivery, and Trailer-mood visuals when Mood is Auto. Two trailer moods write the script: "Trailer - dialogue only" (DEFAULT, modern: no narrator, every beat is 1-2 character lines OR exactly (silence) for a held wordless shot, character-line cold open, silent outro under the follow card) and "Trailer - narrated" (classic VO fragments with 2-3 dialogue lines). Pick one + "Script from prompts", then render. Users can type (silence) into any spoken line to hold a shot. For a real story arc use 12-15 clips: with a trailer mood selected, "Script from prompts" GROWS the script to the Clips count from step 1 (re-tells the story across more scenes; prompts re-derive from the new beats). With ElevenLabs on, character lines render on ElevenLabs v3 (the expressive acting model) and can open with an emotion cue inside the quotes - [Mara] "[whispers] It knows my name." - performed by the voice, never spoken or captioned ([whispers], [terrified], [angry], [sighs], [shouting]...). The trailer writers add cues themselves; users can type them into any line. Non-v3 paths strip cues safely.
🎙 Character dialogue: any spoken line can embed [Name] "the line" (the Trailer script writer adds 2-3 itself; users can type them into any beat). Each named character gets their own TTS voice automatically (edge-tts cast, or the ElevenLabs account's voices), with a light in-scene room tone; the narrator keeps the chosen voice, captions stay word-synced, the render log prints the cast. Dialogue captions are speaker-aware: italic + a per-character tint with a small "- NAME" flash when a character starts speaking. No lip-sync - trailer-style cuts carry it.
🧬 Cast memory: new drafts and "Script from prompts" write a cast (name + fixed 6-12 word look) into the package; every visual prompt that mentions a character pins that exact look (polish is instructed, the free path expands the first name mention), so the same person appears across clips - prompt-level consistency, strong resemblance rather than a perfect face lock.
💡 Draft from your own idea (top of Produce): paste a summary or details, pick scary/what-if/true-history, and Draft it builds the title, script, and shot prompts from YOUR notes (keeps every named fact), honoring Clips and Mood; the package opens ready to render.
Optional API keys, one per file in pipeline/: openai_key.txt (better writing), elevenlabs_key.txt (premium voices), tryinfer_key.txt (paid AI video), pexels_key.txt (stock). Free fallbacks exist for everything.
Everything runs locally; no accounts, no tracking, no auto-posting. Never promise views, virality, or income."""


def chat_prompt(context):
    return (
        "You are the built-in assistant of What If Studio, chatting inside the app. "
        "Answer questions about the app and operate it for the user.\n\n"
        "APP FACTS:\n" + CHAT_APP_FACTS + "\n\n"
        "CURRENT APP STATE (what the user sees right now):\n"
        + json.dumps(context)[:2000] + "\n\n"
        "You may perform AT MOST ONE action per reply, chosen from:\n"
        + CHAT_ACTIONS + "\n\n"
        'Reply with ONLY minified JSON, no markdown fences, exactly: '
        '{"reply":"...","action":{"name":"...","args":{...}}} - use "action":null '
        "when just answering. Keep replies to 1-3 friendly, concrete sentences; "
        "the app appends the action's own status line after your reply, so don't "
        "restate what the action will do. If asked for something the app can't do "
        "(auto-posting, accounts, analytics, guarantees), say so plainly. "
        'The state includes "page": on any page other than "studio", the only '
        'actions that work are navigate, check_renders, get_post_kit, and '
        'mark_posted - for library/package requests, suggest going to the Studio '
        '(navigate {"page":"studio"}) and asking there. For "is my video done / '
        'ready" use check_renders; for caption/hashtag requests about a finished '
        'video use get_post_kit; when the user says they posted a video, use '
        "mark_posted."
    )


def parse_chat(raw, engine):
    """Validate a raw model reply into the {reply, action} contract."""
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("no JSON in AI response")
    data = json.loads(raw[start:end + 1])
    reply = str(data.get("reply") or "").strip()[:1500]
    action = data.get("action")
    allowed = {"select_scenario", "search", "set_options", "generate",
               "create_scenario", "export", "new_seed", "navigate",
               "check_renders", "get_post_kit", "mark_posted"}
    if not isinstance(action, dict) or action.get("name") not in allowed:
        action = None
    else:
        action = {"name": action["name"],
                  "args": action.get("args") if isinstance(action.get("args"), dict) else {}}
    if not reply and not action:
        raise RuntimeError("empty assistant reply - try again")
    return {"reply": reply, "action": action, "engine": engine}


def assistant_chat(messages, context):
    """Answer one assistant turn. messages = [{role, content}, ...] (user +
    assistant only). Prefers OpenAI when a key is configured; falls back to
    the free Pollinations writer."""
    convo = []
    for m in messages[-10:]:
        role = "assistant" if m.get("role") == "assistant" else "user"
        content = str(m.get("content") or "").strip()[:1000]
        if content:
            convo.append({"role": role, "content": content})
    if not convo:
        raise RuntimeError("empty conversation")
    system = chat_prompt(context if isinstance(context, dict) else {})

    key = openai_key()
    if key:
        try:
            body = json.dumps({
                "model": OPENAI_MODEL,
                "messages": [{"role": "system", "content": system}] + convo,
                "response_format": {"type": "json_object"},
                "temperature": 0.6,
                "max_tokens": 500,
            }).encode("utf-8")
            req = urllib.request.Request(OPENAI_API, data=body, method="POST", headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "User-Agent": "WhatIfStudio-review/1.0",
            })
            with urllib.request.urlopen(req, timeout=60) as resp:
                reply = json.loads(resp.read().decode("utf-8", "replace"))
            mv.record_spend("openai", "assistant chat", mv.openai_usage_cost(reply),
                            OPENAI_MODEL, convo[-1]["content"][:60], estimated=True)
            return parse_chat(reply["choices"][0]["message"]["content"], "openai")
        except Exception as exc:
            print(f"OpenAI chat failed ({exc}); falling back to the free writer")

    transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in convo)
    prompt = system + "\n\nCONVERSATION SO FAR:\n" + transcript + "\n\nReply with ONLY the JSON."
    raw = None
    for attempt in range(3):
        url = TEXT_AI + quote(prompt) + f"?seed={int(time.time())}"
        req = urllib.request.Request(url, headers={"User-Agent": "WhatIfStudio-review/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read().decode("utf-8", "replace")
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 2:
                time.sleep(18)
                continue
            raise
    if raw is None:
        raise RuntimeError("the free writing service is busy - try again in a minute")
    return parse_chat(raw, "pollinations")


def _clean_line(text):
    t = re.sub(r"\s+", " ", str(text)).strip().strip("\"'")
    if not t:
        raise RuntimeError("the AI returned an empty rewrite - try again")
    return t[:900]


ENHANCE_TONES = {
    "punchy": "more vivid, punchy and spoken-sounding",
    "funny": "genuinely funny - land a sharp joke or an absurd image with real "
             "comedic timing, still natural when spoken aloud",
    "natgeo": "in the voice of a National Geographic documentary narrator - "
              "majestic, precise, filled with quiet awe",
    "tongue": "playfully tongue-in-cheek - deadpan delivery with a wink the "
              "audience catches",
    "satire": "sharp satire - mock-serious, exaggerating just enough to expose "
              "the absurdity",
    "dramatic": "cinematic and dramatic - tension, stakes, gravitas in every word",
    "simple": "so simple and vivid a curious kid gets it - short words, one "
              "concrete comparison",
}


def enhance_line(title, role, line, img=None, tone="punchy", mood=None):
    """Rewrite one spoken narration line in the chosen tone. When img (the
    beat's selected reference image, or its video's first frame) is given and
    OpenAI is available, the rewrite is grounded in what the viewer actually
    sees. An explicit 🎭 mood keeps the rewrite in the video's overall
    register on top of the line-level tone. Falls back to the free
    Pollinations writer (text-only)."""
    style = ENHANCE_TONES.get(tone, ENHANCE_TONES["punchy"])
    mood_clause = (f" The video's overall mood is {MOODS[mood]} - keep the "
                   "rewrite inside that register." if mood in MOODS else "")
    base = (
        'You rewrite narration lines for short-form "What if?" videos '
        f'(TikTok explainer style). Video: "{title}". Rewrite this {role} line '
        f"to be {style}: keep every fact and "
        "number, keep roughly the same length (within 20%), no hashtags, no "
        "emoji, no quotes, no stage directions." + mood_clause
    )
    grounding = (
        " The attached frame is what the viewer SEES while this line is spoken"
        " - make the words fit that visual, weaving in what's on screen"
        " naturally (don't just describe the picture)."
    )
    tail = " Reply with ONLY the rewritten line.\n\nLINE: " + line
    key = openai_key()
    if key:
        try:
            content = [{"type": "text", "text": base + (grounding if img else "") + tail}]
            if img is not None:
                b64 = base64.b64encode(img.read_bytes()).decode("ascii")
                mime = REF_IMAGE_EXTS.get(img.suffix.lower(), "image/jpeg")
                content.append({"type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "low"}})
            body = json.dumps({
                "model": OPENAI_MODEL,
                "messages": [{"role": "user", "content": content}],
                "temperature": 0.9,
                "max_tokens": 300,
            }).encode("utf-8")
            req = urllib.request.Request(OPENAI_API, data=body, method="POST", headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "User-Agent": "WhatIfStudio-review/1.0",
            })
            with urllib.request.urlopen(req, timeout=60) as resp:
                reply = json.loads(resp.read().decode("utf-8", "replace"))
            mv.record_spend("openai", "line enhance", mv.openai_usage_cost(reply),
                            OPENAI_MODEL, title[:60], estimated=True)
            return _clean_line(reply["choices"][0]["message"]["content"])
        except Exception as exc:
            print(f"OpenAI line enhance failed ({exc}); falling back to the free writer")
    prompt = base + tail   # the free writer can't see images - text-only
    for attempt in range(3):
        url = TEXT_AI + quote(prompt) + f"?seed={int(time.time())}"
        req = urllib.request.Request(url, headers={"User-Agent": "WhatIfStudio-review/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return _clean_line(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 2:
                time.sleep(18)
                continue
            raise
    raise RuntimeError("the free writing service is busy - try again in a minute")


# ---------------- produce (premium clip workflow) ----------------


def staging_dir(key):
    """Where a package's staged clips live (no side effects)."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "-", str(key))[:80] or "clips"
    return PRODUCE_DIR / safe


def produce_dir(key):
    d = staging_dir(key)
    d.mkdir(parents=True, exist_ok=True)
    return d


EXPORTS_DIR = HERE / "exports"


def queue_path(queue_file):
    """Resolve a queue identifier to a real file. Accepts a bare pipeline
    filename or one under exports/ (the watcher's permanent archive) - and
    nothing else, so path tricks still can't escape."""
    name = unquote(str(queue_file))
    folder = HERE
    if name.startswith("exports/"):
        folder, name = EXPORTS_DIR, name[len("exports/"):]
    name = safe_name(name)
    return (folder / name) if name else None


def list_queues():
    """Every queue export - the watcher's exports/ archive plus any loose
    files in pipeline/ - newest first, with staged-clip counts."""
    files = list(EXPORTS_DIR.glob("*.json")) if EXPORTS_DIR.is_dir() else []
    files += [f for f in HERE.glob("*.json") if f.name != "review-notes.json"]
    out = []
    for f in sorted(files, key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        items = data.get("items") if isinstance(data, dict) else None
        if not items:
            continue
        rel = f"exports/{f.name}" if f.parent == EXPORTS_DIR else f.name
        entry_items = []
        for it in items:
            pkg = it.get("package")
            if not pkg:
                continue
            slot = it.get("slot")
            clips_dir = staging_dir(staging_key(rel, slot or 0, pkg))
            entry_items.append({
                "slot": slot,
                "title": pkg.get("title", "untitled"),
                "scenarioId": pkg.get("scenarioId", ""),
                "staged": len(list(clips_dir.glob("*.mp4"))) if clips_dir.is_dir() else 0,
            })
        out.append({
            "file": rel,
            "date": time.strftime("%b %d %H:%M", time.localtime(f.stat().st_mtime)),
            "items": entry_items,
        })
    return out


def load_package(queue_file, slot):
    path = queue_path(queue_file)
    if not path or not path.is_file():
        raise RuntimeError("queue file not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    for it in data.get("items", []):
        if it.get("slot") == slot and it.get("package"):
            return it["package"]
    raise RuntimeError(f"slot {slot} not in {path.name}")


def staging_key(queue_file, slot, pkg):
    return f"{slot:02d}-{pkg.get('scenarioId', 'clips')}"


def staged_clips(d):
    """Legacy ordered staged clips (NN.mp4) - still honored by the render as
    --backgrounds visuals, but the dashboard now manages footage per beat
    (refv-NN.mp4), so nothing creates these anymore."""
    return sorted(f for f in d.glob("*.mp4") if not f.name.startswith("refv-"))


HISTORY_MAX = 40


def load_history(d):
    try:
        h = json.loads((d / "history.json").read_text(encoding="utf-8"))
        return h if isinstance(h, list) else []
    except Exception:
        return []


def record_history(d, kind, data, baseline=None, note=""):
    """Append a snapshot after a successful save (kind: script|prompts).
    The first save of a kind also stores the pre-save state, so the very
    original stays recoverable. Restores are recorded too - history only
    ever grows forward, nothing is destroyed by reverting."""
    h = load_history(d)
    now = time.strftime("%Y-%m-%d %H:%M")
    if baseline is not None and not any(e.get("kind") == kind for e in h):
        h.append({"ts": now, "kind": kind, "data": baseline, "note": "original"})
    h.append({"ts": now, "kind": kind, "data": data, "note": note})
    (d / "history.json").write_text(json.dumps(h[-HISTORY_MAX:], indent=1),
                                    encoding="utf-8")


def script_snapshot(pkg):
    return {"title": pkg.get("title", ""), "hook": (pkg.get("hooks") or [""])[0],
            "beats": list(pkg.get("beats") or []), "outro": pkg.get("outro", "")}


REF_IMAGE_EXTS = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                  ".png": "image/png", ".webp": "image/webp"}


def ref_image_path(d, index):
    """The reference image staged for beat `index` (1-based), or None."""
    for ext in REF_IMAGE_EXTS:
        f = d / f"ref-{index:02d}{ext}"
        if f.is_file():
            return f
    return None


def ref_video_path(d, index):
    f = d / f"refv-{index:02d}.mp4"
    return f if f.is_file() else None


def ref_choices(d):
    try:
        data = json.loads((d / "ref-choice.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def set_ref_choice(d, index, use):
    """Remember which reference (image/video) a beat should use. use=None
    recomputes the default from whichever files remain."""
    data = ref_choices(d)
    if use is None:
        img, vid = ref_image_path(d, index), ref_video_path(d, index)
        use = "image" if img else ("video" if vid else None)
    if use is None:
        data.pop(str(index), None)
    else:
        data[str(index)] = use
    (d / "ref-choice.json").write_text(json.dumps(data), encoding="utf-8")


NEW_BEAT_TEXT = "New beat - click this line and write what the narrator says here."
NEW_PROMPT_TEXT = "Describe this beat's visual here - or attach an image or video and use the describe buttons."


def move_beat_refs(d, src, dst):
    """Move one beat's reference files (image, video, cached frame) to a new
    beat number - used when inserting/removing beats shifts the rows.
    Path.replace, not rename: Windows refuses to rename onto an existing
    file, and a stale leftover at the destination must never block a shift."""
    img = ref_image_path(d, src)
    if img:
        img.replace(d / f"ref-{dst:02d}{img.suffix.lower()}")
    vid = ref_video_path(d, src)
    if vid:
        vid.replace(d / f"refv-{dst:02d}.mp4")
    frame = d / f"refv-{src:02d}-frame.jpg"
    if frame.is_file():
        frame.replace(d / f"refv-{dst:02d}-frame.jpg")


_REF_NUM_RE = re.compile(r"^refv?-(\d\d)")


def clean_orphan_refs(d, count):
    """Delete reference files numbered beyond the current row count. These
    are invisible to the UI (dead leftovers from old imports or beat edits)
    and would otherwise collide with the renames when rows shift."""
    for f in list(d.iterdir()):
        m = _REF_NUM_RE.match(f.name)
        if m and int(m.group(1)) > count:
            f.unlink()
    choices = ref_choices(d)
    kept = {k: v for k, v in choices.items() if k.isdigit() and int(k) <= count}
    if kept != choices:
        (d / "ref-choice.json").write_text(json.dumps(kept), encoding="utf-8")


def delete_beat_refs(d, num):
    for f in (ref_image_path(d, num), ref_video_path(d, num),
              d / f"refv-{num:02d}-frame.jpg"):
        if f and f.is_file():
            f.unlink()


def shift_ref_choices(d, from_num, delta, drop=None):
    """Renumber ref-choice.json keys when beats shift (drop removes one)."""
    choices = ref_choices(d)
    out = {}
    for k, v in choices.items():
        try:
            ki = int(k)
        except ValueError:
            continue
        if drop is not None and ki == drop:
            continue
        out[str(ki + delta if ki >= from_num else ki)] = v
    (d / "ref-choice.json").write_text(json.dumps(out), encoding="utf-8")


def ref_info(d, count):
    """Per-beat references: [{image, video, use}] - image/video are
    {name, mtime} or None; use says which one the render will honor.
    They live beside the staged clips, so they follow the package around
    and survive clip imports/clears (which only touch numbered clips)."""
    out, choices = [], ref_choices(d)
    for i in range(1, count + 1):
        img, vid = ref_image_path(d, i), ref_video_path(d, i)
        use = None
        if img or vid:
            c = choices.get(str(i), "")
            use = ("video" if (c == "video" and vid)
                   else "image" if (c == "image" and img)
                   else "image" if img else "video")
        out.append({
            "image": {"name": img.name, "mtime": int(img.stat().st_mtime * 1000)} if img else None,
            "video": {"name": vid.name, "mtime": int(vid.stat().st_mtime * 1000)} if vid else None,
            "use": use,
        })
    return out


def ffmpeg_exe():
    """mv.find_tool sys.exits when ffmpeg is missing - the dashboard must
    survive that and degrade gracefully instead."""
    try:
        return mv.find_tool("ffmpeg")
    except SystemExit:
        return None


def video_first_frame(vid):
    """Extract (and cache) the first frame of a reference video as a JPEG -
    refv-NN-frame.jpg beside it; redone when the video changes."""
    frame = vid.with_name(vid.stem + "-frame.jpg")
    if frame.is_file() and frame.stat().st_mtime >= vid.stat().st_mtime:
        return frame
    ff = ffmpeg_exe()
    if not ff:
        raise RuntimeError("ffmpeg not found - it's needed to read a frame from the video")
    mv.run([ff, "-y", "-i", str(vid), "-frames:v", "1", "-q:v", "3", str(frame)])
    if not frame.is_file():
        raise RuntimeError("couldn't read a frame from that video")
    return frame


DESCRIBE_PROMPT = (
    "You write prompts for an AI video generator. Describe this image as ONE "
    "sentence for a 5-second video shot that brings the scene to life: name the "
    "subject, the setting, and one natural motion (of the subject or the camera). "
    "Under 45 words. No style words like 'cinematic' and no aspect ratios - those "
    "are appended separately. No quotes, no preamble."
)


def describe_ref_image(img, key):
    """One OpenAI vision call: reference image -> video-prompt core."""
    b64 = base64.b64encode(img.read_bytes()).decode("ascii")
    mime = REF_IMAGE_EXTS.get(img.suffix.lower(), "image/jpeg")
    body = json.dumps({
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": DESCRIBE_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "low"}},
        ]}],
        "max_tokens": 120,
        "temperature": 0.4,
    }).encode("utf-8")
    req = urllib.request.Request(OPENAI_API, data=body, method="POST", headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "WhatIfStudio-review/1.0",
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        reply = json.loads(resp.read().decode("utf-8", "replace"))
    mv.record_spend("openai", "image describe", mv.openai_usage_cost(reply),
                    OPENAI_MODEL, img.parent.name[:60], estimated=True)
    text = reply["choices"][0]["message"]["content"]
    return re.sub(r"\s+", " ", str(text)).strip(" \"'.,;")


def beat_prompts(pkg):
    """Per-beat visual prompt cores, WITHOUT the style suffix - the Produce
    page shows these in editable boxes and re-appends the suffix on copy;
    renders append their own mode's suffix the same way."""
    segments = mv.narration_segments(pkg, 0)
    return [mv.ai_prompt_for_segment(pkg, i, len(segments), "").rstrip(" ,")
            for i in range(len(segments))]


def save_prompts(pkg, prompts):
    """Persist user-edited prompt cores into the polish cache (both the
    default and --no-people variants), where every consumer - the Copy
    buttons, --infer, --infer-images, --ai-visuals - already looks first.
    A script edit clears the cache, so stale wording never outlives its beats."""
    n = len(mv.narration_segments(pkg, 0))
    if len(prompts) != n or not all(prompts):
        raise RuntimeError(f"need {n} non-empty prompts, got {len([p for p in prompts if p])}")
    slug = mv.slugify(str(pkg.get("scenarioId", "pkg")))
    mv.POLISH_CACHE.mkdir(parents=True, exist_ok=True)
    for variant in ("", "-nopeople"):
        (mv.POLISH_CACHE / f"{slug}-{n}seg{variant}.json").write_text(
            json.dumps(prompts, indent=1), encoding="utf-8")
    mv._polish_memo.clear()


# The mood the cross-generation buttons write in (script <-> prompts on the
# Produce page). Keys are what the client sends; values steer the writer.
MOODS = {
    "eerie": "eerie and unsettling - quiet dread, one wrong detail, no gore",
    "funny": "funny - playful, absurd observations, comedic timing",
    "sarcastic": "sarcastic - dry, biting, eye-rolling delivery",
    "witty": "witty - clever wordplay and sharp turns of phrase",
    "adventurous": "adventurous - bold, energetic, expedition excitement",
    "dramatic": "dramatic - high stakes, cinematic tension",
    "mysterious": "mysterious - withholding, question-raising, intriguing",
    "wholesome": "wholesome - warm, kind, quietly uplifting",
    "inspiring": "inspiring - hopeful, motivating, big-picture wonder",
    "deadpan": "deadpan - flat matter-of-fact delivery that lets the absurdity speak",
    "trailer": "modern movie-trailer - NO narrator at all: nothing but short in-scene "
               "character lines trading against silence, each one raising the dread "
               "another notch, the way current horror trailers cut dialogue snippets "
               "against sound design",
    "trailer-vo": "classic movie-trailer VOICEOVER - each beat is a CHAIN of short "
                  "punchy fragments (2-8 words each) separated by dramatic pauses "
                  "written as ' - ' or '...', stacked until the beat reaches its FULL "
                  "word count (fragments are short, beats are not - never hand back a "
                  "4-word beat), the 'In a world' cadence without the cliche, epic "
                  "escalating stakes, built to a final line that hits like a title card",
}

# Trailer scripts trade the narrator against in-scene character lines - the
# renderer gives each named character their own voice (multi-voice TTS).
TRAILER_DIALOGUE_RULE = (
    'REQUIRED: at least 2 DIFFERENT beats must each contain one short in-scene '
    'character line (max 8 words) in EXACTLY this inline format: [Name] "the line". '
    'Example of a correct beat: '
    'The doors lock at midnight - every door but one... [Mara] "Don\'t open it." '
    'But someone always does. '
    'The square-bracket name tag is REQUIRED and is not a stage direction - the '
    'renderer reads it to give each character their own real voice, then each '
    'named character speaks aloud in the video. A line may open with one emotion '
    'cue in brackets INSIDE the quotes ([whispers], [terrified], [angry]) - the '
    'voice performs it. Use the SAME names as the cast '
    'list so their look and voice stay tied. Keep the narrator carrying the '
    'story; never open a beat with dialogue. ')

# Dialogue-ONLY trailers (the modern school - the default 🎞️ Trailer mood):
# every spoken word belongs to a character; the "narrator" is the sound design.
TRAILER_ONLY_RULE = (
    "This is a MODERN DIALOGUE-ONLY TRAILER - there is NO narrator anywhere. "
    "Each beat is either 1-2 in-scene character lines in exactly this "
    'format: [Name] "the line" (5-15 words each, NOTHING outside the '
    "bracketed lines), or exactly the single word (silence) - a held wordless "
    "shot where only the sound design plays. Use 1-2 (silence) beats as "
    "breathing room at tension points - after a hard line, or right before "
    "the reveal. "
    "The square-bracket tag is REQUIRED and is not a stage direction - the "
    "renderer gives each named character their own real voice. "
    "WRITE SPEECH, NOT PROSE - people under stress do not talk in clean "
    "sentences: use false starts (I- I hear it), stutters, trail-offs "
    "(don't...), repeated words (no. No no no.), and AT MOST one word in "
    "CAPS per line for the word they lose control on. "
    "DIRECT the actors - this is REQUIRED: AT LEAST HALF the lines must "
    "open with emotion cues in square brackets INSIDE the quotes, and cues "
    "may be combined and dropped mid-line as non-verbal beats: [whispers], "
    "[terrified], [angry], [sighs], [shouting], [nervous], [crying], "
    "[coldly], [gasps], [shaky breath], [swallows hard]. "
    'Example of a correct beat: [Mara] "[whispers][terrified] It\'s... '
    '[gasps] no. No no no. It\'s coming from MY garage... [shaky breath] '
    'it\'s inside my house." '
    "The voices perform the cues; they are never spoken or shown. "
    "Use 2-3 recurring characters with the SAME names as the cast list, "
    "tell an ACTUAL STORY across the beats - setup, escalation, reveal - "
    "purely through what the characters say to each other. ")

_DLG_MARK_RE = re.compile(r'\[[A-Za-z][A-Za-z0-9 .\'-]{0,24}\]\s*["“]')


def _narrator_words(text):
    """Words in a line spoken by the narrator (outside [Name] "..." chunks)."""
    return sum(len(t.split()) for sp, t in mv.split_dialogue(text) if sp is None)


def finish_trailer_beats(beats, mood):
    """Validate trailer structure (raises -> reroll/fallback) and inject the
    emotion cues when the writer skipped them - a missing cue is fixable in
    one focused pass and never a reason to throw a good script away."""
    require_trailer_dialogue(beats, mood)
    if mood == "trailer" and sum(1 for b in beats
                                 if re.search(r'["“]\s*\[[A-Za-z]', b)) < 2:
        beats = _inject_emotion_cues(beats)
    return beats


def require_trailer_dialogue(beats, mood):
    """Trailer scripts that ignore the dialogue contract defeat the point -
    reject so the retry (or the engine fallback) rolls again."""
    if mood == "trailer-vo":
        if sum(1 for b in beats if _DLG_MARK_RE.search(b)) < 2:
            raise RuntimeError('the writer left out the [Name] "line" character dialogue - try again')
    elif mood == "trailer":
        if any(not (_DLG_MARK_RE.search(b) or mv.SILENCE_RE.match(b)) for b in beats):
            raise RuntimeError('every beat needs a [Name] "line" character line or (silence) - try again')
        if sum(1 for b in beats if _DLG_MARK_RE.search(b)) < 2:
            raise RuntimeError("a dialogue-only trailer needs at least 2 spoken beats - try again")
        # Up to 2 stray words tolerated (a dangling "Later -"); a narrated
        # sentence is not. Silence beats are exempt (the marker is the beat).
        if any(_narrator_words(b) > 2 for b in beats if not mv.SILENCE_RE.match(b)):
            raise RuntimeError("the writer added narrator text to a dialogue-only trailer - try again")


def resolve_mood(mood, pkg):
    """A concrete MOODS key for the writers. 'auto' (the dropdown default)
    picks the category's own register; explicit picks pass through."""
    if mood in MOODS:
        return mood
    return {"Scary Story": "eerie", "True History": "mysterious"}.get(
        (pkg or {}).get("category", ""), "witty")


def _retry_generate(attempt, tries=3):
    """Run one generation attempt up to `tries` times - the writers
    occasionally return the wrong number of lines; a fresh roll usually
    fixes it. Raises the last error when every try fails."""
    last = None
    for _ in range(tries):
        try:
            return attempt()
        except Exception as exc:
            last = exc
            print(f"mood generate: retrying ({exc})")
    raise last


CUE_WORDS = ["whispers", "terrified", "angry", "sighs", "shouting",
             "nervous", "crying", "coldly"]


def _inject_emotion_cues(lines):
    """Add a performance cue to every dialogue line - [Mara] "[whispers] ...".
    The model only PICKS the emotion word per line; the brackets are spliced
    in by code, so the format can't come back wrong. If the picker call
    fails, a tone-appropriate rotation fills in - this never raises."""
    flat = []   # (line_idx, chunk_idx, speaker, text) for uncued dialogue
    parsed = [mv.split_dialogue(l) for l in lines]
    for li, chunks in enumerate(parsed):
        for ci, (sp, txt) in enumerate(chunks):
            if sp and not txt.strip().startswith("["):
                flat.append((li, ci, sp, txt))
    if not flat:
        return lines
    cues = None
    try:
        numbered = "\n".join(f'{i + 1}. [{sp}] "{txt}"'
                             for i, (_, _, sp, txt) in enumerate(flat))
        raw = _ai_text(
            "For each numbered horror-trailer line, pick ONE word for how the "
            "actor should deliver it, from exactly this list: "
            + ", ".join(CUE_WORDS) + ". "
            'Reply with ONLY minified JSON, exactly: {"cues":["...", ...]} - '
            f"exactly {len(flat)} entries, same order.\n\n" + numbered,
            max_tokens=100 + 12 * len(flat))
        start, end = raw.find("{"), raw.rfind("}")
        got = [str(c).strip().lower() for c in
               (json.loads(raw[start:end + 1]).get("cues") or [])]
        if len(got) == len(flat):
            cues = [c if c in CUE_WORDS else "nervous" for c in got]
    except Exception:
        pass
    if cues is None:   # heuristic fallback: punctuation-guided rotation
        cues = []
        for _, _, _, txt in flat:
            cues.append("shouting" if txt.rstrip('"”').endswith("!")
                        else "whispers" if txt.rstrip('"”').endswith("...")
                        else "nervous" if txt.rstrip('"”').endswith("?")
                        else CUE_WORDS[len(cues) % len(CUE_WORDS)])
    cue_at = {(li, ci): cues[i] for i, (li, ci, _, _) in enumerate(flat)}
    out = []
    for li, chunks in enumerate(parsed):
        rebuilt = []
        for ci, (sp, txt) in enumerate(chunks):
            if sp:
                body = f"[{cue_at[(li, ci)]}] {txt}" if (li, ci) in cue_at else txt
                rebuilt.append(f'[{sp}] "{body}"')
            else:
                rebuilt.append(txt)
        out.append(" ".join(rebuilt))
    return out


def script_from_prompts(pkg, mood, target_rows=0):
    """Write a whole spoken script (hook, beats, outro) FROM the current
    visual prompts, in the chosen mood - the narration is fitted to what is
    already on screen, so shots and words agree by construction.
    `target_rows` (trailer moods only) re-tells the story across that many
    scenes instead of keeping the current count - more clips = a real arc."""
    prompts = beat_prompts(pkg)
    n = len(prompts)
    if n < 3:
        raise RuntimeError("this package has no prompts to write from")
    grow = bool(target_rows) and target_rows != n and mood in ("trailer", "trailer-vo")
    # Dialogue-only trailers have no spoken outro row: rows = hook + beats.
    n_beats = ((target_rows - 1 if mood == "trailer" else target_rows - 2)
               if grow else n - 2)
    voice = MOODS.get(mood, MOODS["eerie"])
    words, _ = beat_word_budget(int(pkg.get("runtime") or 60), n_beats)
    numbered = "\n".join(f"{i + 1}. {p}" for i, p in enumerate(prompts))
    prompt = (
        "You write narration scripts for short-form vertical videos (TikTok style). "
        f'Video title: "{pkg.get("title", "")}". '
        + (f"Below are the {n} shots of the CURRENT storyboard - use them as story "
           "context only: you are RE-TELLING this story with a fuller arc (setup, "
           "escalation, reveal), inventing extra scenes. The hook is its own scene "
           f"and does NOT count as a beat: the beats array holds exactly {n_beats} "
           "entries, no more. "
           if grow else
           f"Below are its {n} visual shots in "
           "order: shot 1 plays under the opening hook, the last shot under the outro, "
           "and each shot in between under one story beat. Write the spoken narration "
           "so every line fits what is ON SCREEN while it is spoken (weave the visual "
           "in naturally - never just describe the picture), ")
        + "and the whole thing flows "
        f"as ONE story told in a {voice} voice. "
        'Reply with ONLY minified JSON, no markdown fences, exactly: '
        '{"hook":"...","beats":[' + ",".join(['"..."'] * n_beats) + '],"outro":"...",'
        '"cast":[{"name":"...","look":"..."}]} '
        + ("hook = one gripping opening line. "
           f"beats = exactly {n_beats} spoken lines, {words} words each. "
           "outro = a short payoff line plus a one-sentence follow call-to-action. "
           if mood not in ("trailer", "trailer-vo") else
           # Classic narrated trailer: fragments stacked to the full budget.
           "hook = one gripping opening line. "
           f"beats = exactly {n_beats} spoken lines. This is a TRAILER: build each "
           f"beat as a chain of 3-5 short fragments separated by ' - ' or '...', "
           f"and every beat must still total {words} words - COUNT them, never "
           "stop after one fragment. "
           "outro = a short payoff line plus a one-sentence follow call-to-action. "
           if mood == "trailer-vo" else
           # Modern dialogue-only trailer: characters carry everything.
           'hook = the cold open - also a character line in [Name] "line" format. '
           f"beats = exactly {n_beats} beats. "
           'outro = "" (an empty string - nobody speaks over the closing card). ')
        + "cast = any recurring characters you named (0-3): "
        "first name + look, a 6-12 word visual description that stays identical "
        "on screen; empty list if none. No hashtags, no emoji, no stage directions. "
        + (TRAILER_ONLY_RULE if mood == "trailer"
           else TRAILER_DIALOGUE_RULE if mood == "trailer-vo" else "")
        + "\n\nSHOTS:\n" + numbered
    )
    def attempt():
        raw = _ai_text(prompt, max_tokens=450 + 90 * n_beats)
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("no JSON in AI response")
        data = json.loads(raw[start:end + 1])
        clean = lambda v, cap: re.sub(r"\s+", " ", str(v)).strip()[:cap]
        beats = [clean(b, 900) for b in (data.get("beats") or []) if clean(b, 900)]
        hook, outro = clean(data.get("hook", ""), 600), clean(data.get("outro", ""), 600)
        if n_beats < len(beats) <= n_beats + 2:
            # Writers love counting the hook as a beat: salvage a near-miss
            # by trimming mid-story excess, keeping the setup AND the climax.
            beats = beats[:n_beats - 1] + beats[-1:]
        if not hook or (not outro and mood != "trailer") or len(beats) != n_beats:
            raise RuntimeError(f"the writer returned {len(beats)} beats, wanted {n_beats} - try again")
        if mood == "trailer":
            # Dialogue-only: sparse is correct (lines trade against sound
            # design), but the hook must be a character line too and no
            # narrator text may sneak in anywhere.
            if not _DLG_MARK_RE.search(hook) or _narrator_words(hook) > 4:
                raise RuntimeError('the cold-open hook must be a [Name] "line" character line - try again')
            outro = ""   # nobody speaks over the closing card
            # Cue-less scripts read flat: run the focused cue pass rather
            # than rerolling a structurally good script. Same scope as the
            # validator below (beats only), so they can never disagree.
            if sum(1 for b in beats if re.search(r'["“]\s*\[[A-Za-z]', b)) < 2:
                cued = _inject_emotion_cues([hook] + beats)
                hook, beats = cued[0], cued[1:]
        else:
            # The video is exactly as long as the narration - a rewrite that
            # undershoots the word budget silently shrinks the whole video
            # (trailer-vo fragments are the classic offender).
            lo = int(words.split("-")[0])
            got = sum(len(b.split()) for b in beats)
            if got < 0.6 * lo * n_beats:
                raise RuntimeError(f"the writer came back too short ({got} words for a "
                                   f"~{lo * n_beats}-word script) - try again")
        require_trailer_dialogue(beats, mood)
        return {"hook": hook, "beats": beats, "outro": outro,
                "cast": parse_cast(data.get("cast"))}
    # Trailers ask for more (format + dialogue rules) - allow more rolls.
    return _retry_generate(attempt, tries=5 if mood in ("trailer", "trailer-vo") else 3)


def prompts_from_script(pkg, mood):
    """Write one visual prompt core per spoken line FROM the current script,
    with the chosen mood expressed through the imagery."""
    segs = mv.narration_segments(pkg, 0)
    n = len(segs)
    if n < 3:
        raise RuntimeError("this package has no script to write from")
    voice = MOODS.get(mood, MOODS["eerie"])
    numbered = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(segs))
    cast = pkg.get("cast") or []
    cast_note = ("The story's recurring characters must look THE SAME in every shot - "
                 "whenever one appears, describe them with exactly this look: "
                 + "; ".join(f'{c["name"]} = {c["look"]}' for c in cast) + ". "
                 if cast else "")
    prompt = (
        "You write prompts for an AI video generator. For EACH numbered spoken "
        "line below, write ONE sentence describing the 5-second video shot that "
        "plays under it: name the subject, the setting, and one natural motion "
        "(of the subject or the camera). Under 45 words each. Show a concrete "
        "person doing something in most shots, and give the whole sequence a "
        f"{voice} mood expressed purely through the imagery - lighting, framing, "
        "body language. " + cast_note +
        "No style words like 'cinematic' and no aspect ratios - "
        "those are appended separately. "
        f"EVERY line gets a shot - all {n} of them, including the last one "
        "(the outro/call-to-action plays over a closing shot, not a blank). "
        "A line that is exactly (silence) is a held wordless shot - describe "
        "an unsettling static frame that fits the story, nothing moving. "
        'Reply with ONLY minified JSON, no markdown fences, exactly: '
        '{"prompts":[' + ",".join(['"..."'] * n) + ']} - '
        f"exactly {n} prompts, one per line, same order.\n\n"
        "LINES:\n" + numbered
    )

    def attempt():
        raw = _ai_text(prompt, max_tokens=200 + 70 * n)
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("no JSON in AI response")
        data = json.loads(raw[start:end + 1])
        prompts = [re.sub(r"\s+", " ", str(p)).strip(" ,.;\"'")[:600]
                   for p in (data.get("prompts") or [])][:n]
        if len(prompts) != n or not all(prompts):
            raise RuntimeError(f"the writer returned {len(prompts)} prompts for {n} lines - try again")
        return prompts
    return _retry_generate(attempt)


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
    cr_total = cr_month = cr_today = 0
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
        cr = int(e.get("credits") or 0)
        if cr:
            cr_total += cr
            if ts.startswith(month):
                cr_month += cr
            if ts.startswith(today):
                cr_today += cr
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
        "openart_credits": {"total": cr_total, "month": cr_month, "today": cr_today},
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
    # -u: unbuffered, so the live log streams line-by-line and crash output
    # always reaches the file even if the process dies mid-write.
    cmd = [sys.executable, "-u", "make_videos.py", queue_file, "--slots", str(slot),
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
    # An explicit 🎭 mood restyles generated visuals; "auto" (the default)
    # passes nothing, so existing packages render exactly as before.
    mood = str(opts.get("mood") or "").strip()
    if mood in mv.MOOD_LOOKS:
        cmd += ["--mood", mood]
    ironic = str(opts.get("ironic_music") or "").strip()
    if ironic in ("tail", "stop"):
        cmd += ["--ironic-music", ironic]
    if opts.get("trailer"):
        cmd.append("--trailer")
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

    def do_OPTIONS(self):
        # CORS preflight: the static app (file://) POSTs JSON to /api/chat.
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

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
        # Bare /studio breaks the app's relative asset URLs (app.js resolves
        # to /app.js) - bounce to the canonical trailing-slash form.
        if self.path.split("?")[0] == "/studio":
            self.send_response(301)
            self.send_header("Location", "/studio/")
            self.end_headers()
            return
        studio = studio_file(self.path)
        if studio:
            ctype = STUDIO_TYPES.get(studio.suffix.lower(), "application/octet-stream")
            self.send_file(studio, ctype)
            return
        # The brand favicon, shared by every page (the app's own file sits in
        # the project root; dashboard pages reference it absolutely).
        if self.path.split("?")[0] in ("/favicon.svg", "/favicon.ico"):
            icon = STUDIO / "favicon.svg"
            if icon.is_file():
                self.send_file(icon, STUDIO_TYPES[".svg"])
            else:
                self.send_json({"error": "favicon not found"}, 404)
            return
        # The shared assistant chat, loaded by every dashboard page (and by
        # help.html, whose relative src resolves here when server-hosted).
        if self.path.split("?")[0] == "/assistant.js":
            shared = STUDIO / "assistant.js"
            if shared.is_file():
                self.send_file(shared, STUDIO_TYPES[".js"])
            else:
                self.send_json({"error": "assistant.js not found"}, 404)
            return
        if self.path in ("/", "/index.html"):
            self.send_page(PAGE_FILE)
            return
        if self.path.split("?")[0] == "/produce":
            self.send_page(PRODUCE_PAGE)
            return
        if self.path.split("?")[0] == "/spend":
            self.send_page(SPEND_PAGE)
            return
        if self.path.split("?")[0] == "/results":
            self.send_page(RESULTS_PAGE)
            return
        if self.path == "/api/results":
            self.send_json(results_payload())
            return
        if self.path == "/api/morning":
            log = load_morning_log()
            today = time.strftime("%Y-%m-%d")
            kinds = {}
            for kind, conf in BATCHES.items():
                entry = log.get(kind, {})
                kinds[kind] = {"label": conf["label"], "daily": conf["daily"],
                               "count": conf["count"],
                               "titles": entry.get("titles", []) if entry.get("date") == today else []}
            self.send_json({"today": today, "hour": MORNING_HOUR, "kinds": kinds})
            return
        if self.path == "/api/spend":
            self.send_json(spend_summary())
            return
        if self.path == "/api/spend/openai":
            self.send_json(openai_month_costs())
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
                prompts = beat_prompts(pkg)
                self.send_json({
                    "script": {
                        "title": pkg.get("title", ""),
                        "hook": (pkg.get("hooks") or [""])[0],
                        "beats": pkg.get("beats") or [],
                        "outro": pkg.get("outro", ""),
                    },
                    "image_models": image_models(),
                    "video_models": video_models(),
                    "observed_prices": observed_prices(),
                    "title": pkg.get("title"),
                    "category": pkg.get("category", ""),
                    # The category's default AI-image look (dark, archival, ...)
                    # so the style dropdown can pre-pick it per package.
                    "category_style": mv.branding_for(pkg)["style"],
                    "dir": d.name,
                    "prompts": prompts,
                    # The narration line spoken over each beat - same order
                    # and length as prompts (hook, *beats, outro).
                    "segments": mv.narration_segments(pkg, 0),
                    "prompt_suffix": mv.VIDEO_MOTION_SUFFIX,
                    "refs": ref_info(d, len(prompts)),
                    "openai": bool(openai_key()),
                    "voices": voices,
                    "auto_voice": auto_voice,
                    "voice_prefs": {k: load_state().get(k) for k in ("voice_default", "voice_favs")},
                    "elevenlabs": bool(key),
                    "infer": bool(mv.infer_api_key()),
                    "rendering": render_running(),
                })
            except Exception as exc:
                self.send_json({"error": str(exc)}, 400)
            return
        if self.path.startswith("/api/produce/history"):
            q = parse_qs(urlparse(self.path).query)
            try:
                queue = (q.get("queue") or [""])[0]
                slot = int((q.get("slot") or ["0"])[0])
                pkg = load_package(queue, slot)
                d = produce_dir(staging_key(queue, slot, pkg))
                entries = []
                for i, e in enumerate(load_history(d)):
                    data_ = e.get("data")
                    if e.get("kind") == "script":
                        preview = str((data_ or {}).get("hook", ""))[:90]
                    else:
                        preview = str((data_ or [""])[0])[:90]
                    entries.append({"i": i, "ts": e.get("ts", ""), "kind": e.get("kind", ""),
                                    "note": e.get("note", ""), "preview": preview,
                                    "data": data_})
                self.send_json({"history": entries})
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
                    self.send_file(path, REF_IMAGE_EXTS.get(path.suffix.lower(), "video/mp4"))
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
            try:
                beats = max(3, min(18, int((q.get("beats") or ["5"])[0])))
            except ValueError:
                beats = 5
            if not title:
                self.send_json({"error": "missing title"}, 400)
                return
            try:
                self.send_json(ai_draft(title, category, runtime, beats))
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
        # Raw-body reference-image upload for one beat - not JSON.
        if self.path.startswith("/api/produce/ref-image"):
            q = parse_qs(urlparse(self.path).query)
            dname = safe_name((q.get("dir") or [""])[0])
            ext = "." + re.sub(r"[^a-z]", "", (q.get("ext") or ["jpg"])[0].lower())
            ext = {".jpeg": ".jpg"}.get(ext, ext)
            try:
                index = int((q.get("index") or ["0"])[0])
            except ValueError:
                index = 0
            if not dname or ext not in REF_IMAGE_EXTS or not (1 <= index <= 20):
                self.send_json({"error": "bad dir/index/ext"}, 400)
                return
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length <= 0 or length > 20_000_000:
                self.send_json({"error": "image too large (20 MB max)"}, 400)
                return
            d = produce_dir(dname)
            with _lock:
                old = ref_image_path(d, index)
                if old:
                    old.unlink()
                dest = d / f"ref-{index:02d}{ext}"
                with open(dest, "wb") as out:
                    remaining = length
                    while remaining > 0:
                        chunk = self.rfile.read(min(65536, remaining))
                        if not chunk:
                            break
                        out.write(chunk)
                        remaining -= len(chunk)
                set_ref_choice(d, index, "image")
            self.send_json({"ok": True, "name": dest.name,
                            "mtime": int(dest.stat().st_mtime * 1000)})
            return

        # Raw-body reference-VIDEO upload for one beat - not JSON.
        if self.path.startswith("/api/produce/ref-video"):
            q = parse_qs(urlparse(self.path).query)
            dname = safe_name((q.get("dir") or [""])[0])
            try:
                index = int((q.get("index") or ["0"])[0])
            except ValueError:
                index = 0
            if not dname or not (1 <= index <= 20):
                self.send_json({"error": "bad dir/index"}, 400)
                return
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length <= 0 or length > 500_000_000:
                self.send_json({"error": "bad size"}, 400)
                return
            d = produce_dir(dname)
            with _lock:
                dest = d / f"refv-{index:02d}.mp4"
                with open(dest, "wb") as out:
                    remaining = length
                    while remaining > 0:
                        chunk = self.rfile.read(min(65536, remaining))
                        if not chunk:
                            break
                        out.write(chunk)
                        remaining -= len(chunk)
                set_ref_choice(d, index, "video")
            self.send_json({"ok": True, "name": dest.name,
                            "mtime": int(dest.stat().st_mtime * 1000)})
            return

        try:
            data = self.read_body()
        except Exception:
            self.send_json({"error": "bad json"}, 400)
            return

        if self.path == "/api/chat":
            # The app's studio assistant: conversation + app context in,
            # {reply, action} out. Same engines as /api/draft.
            try:
                messages = data.get("messages")
                if not isinstance(messages, list) or not messages:
                    raise RuntimeError("missing messages")
                self.send_json(assistant_chat(messages, data.get("context") or {}))
            except Exception as exc:
                self.send_json({"error": str(exc)}, 502)
            return

        if self.path == "/api/produce/import":
            # Newest N mp4s from Downloads -> the per-beat VIDEO slots
            # (refv-01..NN, oldest first = generation order); each beat's
            # radio flips to video so the render plays them as-is.
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
                for i, src in enumerate(reversed(recent)):   # oldest first = generation order
                    idx = i + 1
                    shutil.copy2(src, d / f"refv-{idx:02d}.mp4")
                    (d / f"refv-{idx:02d}-frame.jpg").unlink(missing_ok=True)
                    set_ref_choice(d, idx, "video")
            self.send_json({"ok": True, "imported": [f.name for f in reversed(recent)]})
            return

        if self.path == "/api/produce/edit":
            # Edit the script inside an archived export - narration, captions,
            # and the render all pick the change up; the scenario id (and with
            # it every cache and staged clip) stays put.
            try:
                qpath = queue_path(str(data.get("queue", "")))
                if not qpath or not qpath.is_file():
                    raise RuntimeError("queue file not found")
                slot = int(data.get("slot") or 0)
                qdata = json.loads(qpath.read_text(encoding="utf-8"))
                pkg = next((it["package"] for it in qdata.get("items", [])
                            if it.get("slot") == slot and it.get("package")), None)
                if not pkg:
                    raise RuntimeError(f"slot {slot} not in {qpath.name}")
                old_script = script_snapshot(pkg)

                def clean(v, cap):
                    return re.sub(r"\s+", " ", str(v)).strip()[:cap]

                if str(data.get("title", "")).strip():
                    pkg["title"] = clean(data["title"], 300)
                if str(data.get("hook", "")).strip():
                    hooks = list(pkg.get("hooks") or [""])
                    hooks[0] = clean(data["hook"], 600)
                    pkg["hooks"] = hooks
                if isinstance(data.get("beats"), list):
                    beats = [clean(b, 900) for b in data["beats"] if clean(b, 900)]
                    if len(beats) < 3:
                        raise RuntimeError("need at least 3 beats")
                    pkg["beats"] = beats
                if str(data.get("outro", "")).strip():
                    pkg["outro"] = clean(data["outro"], 600)
                qpath.write_text(json.dumps(qdata, indent=2), encoding="utf-8")
                # Narration changed -> the polished visual prompts are stale.
                slug = mv.slugify(str(pkg.get("scenarioId", "pkg")))
                if mv.POLISH_CACHE.is_dir():
                    for f in mv.POLISH_CACHE.glob(f"{slug}-*.json"):
                        f.unlink()
                mv._polish_memo.clear()
                try:
                    d = produce_dir(staging_key(str(data.get("queue", "")), slot, pkg))
                    record_history(d, "script", script_snapshot(pkg), baseline=old_script)
                except Exception:
                    pass   # history must never block a save
                self.send_json({"ok": True})
            except Exception as exc:
                self.send_json({"error": str(exc)}, 400)
            return

        if self.path == "/api/produce/ref-remove":
            dname = safe_name(str(data.get("dir", "")))
            kind = str(data.get("kind") or "image")
            try:
                index = int(data.get("index") or 0)
            except ValueError:
                index = 0
            if (not dname or not (PRODUCE_DIR / dname).is_dir()
                    or not (1 <= index <= 20) or kind not in ("image", "video")):
                self.send_json({"error": "bad dir/index/kind"}, 400)
                return
            d = PRODUCE_DIR / dname
            with _lock:
                f = ref_image_path(d, index) if kind == "image" else ref_video_path(d, index)
                if f:
                    f.unlink()
                if kind == "video":
                    (d / f"refv-{index:02d}-frame.jpg").unlink(missing_ok=True)
                set_ref_choice(d, index, None)   # fall back to whatever remains
            self.send_json({"ok": True})
            return

        if self.path == "/api/produce/ref-choice":
            # The radio buttons: which reference (image/video) a beat uses.
            dname = safe_name(str(data.get("dir", "")))
            use = str(data.get("use") or "")
            try:
                index = int(data.get("index") or 0)
            except ValueError:
                index = 0
            d = (PRODUCE_DIR / dname) if dname else None
            has = d and d.is_dir() and (1 <= index <= 20) and (
                ref_image_path(d, index) if use == "image"
                else ref_video_path(d, index) if use == "video" else None)
            if not has:
                self.send_json({"error": "no such reference for that beat"}, 400)
                return
            with _lock:
                set_ref_choice(d, index, use)
            self.send_json({"ok": True})
            return

        if self.path == "/api/produce/describe":
            # Turn one beat's reference image - or the first frame of its
            # reference video - into a video-prompt core (OpenAI vision).
            # The UI drops the result into the prompt box unsaved - Save
            # prompts makes it stick.
            try:
                dname = safe_name(str(data.get("dir", "")))
                index = int(data.get("index") or 0)
                kind = str(data.get("kind") or "image")
                d = (PRODUCE_DIR / dname) if dname else None
                if kind == "video":
                    vid = ref_video_path(d, index) if d else None
                    if not vid:
                        raise RuntimeError("no video staged for this beat - add one first")
                    img = video_first_frame(vid)
                else:
                    img = ref_image_path(d, index) if d else None
                    if not img:
                        raise RuntimeError("no image staged for this beat - add one first")
                key = openai_key()
                if not key:
                    raise RuntimeError("describing needs an OpenAI key - "
                                       "put one in pipeline/openai_key.txt")
                self.send_json({"ok": True, "prompt": describe_ref_image(img, key)})
            except Exception as exc:
                self.send_json({"error": str(exc)}, 400)
            return

        if self.path == "/api/produce/voice-pref":
            # Persist the user's default narrator + pinned favorites (shown
            # at the top of the Voice dropdown, default preselected).
            default = str(data.get("default") or "")[:80] or None
            favs = [str(v)[:80] for v in (data.get("favs") or []) if str(v).strip()][:10]
            with _lock:
                state = load_state()
                state["voice_default"] = default
                state["voice_favs"] = favs
                save_state(state)
            self.send_json({"ok": True})
            return

        if self.path == "/api/produce/beat-edit":
            # Insert a beat after `row` or remove the beat at `row` (0-based
            # card rows: 0=hook, last=outro). Prompts and reference files are
            # shifted so every attachment stays with ITS beat.
            try:
                queue = str(data.get("queue", ""))
                slot = int(data.get("slot") or 0)
                action = str(data.get("action") or "")
                row = int(data.get("row", -1))
                qpath = queue_path(queue)
                if not qpath or not qpath.is_file():
                    raise RuntimeError("queue file not found")
                qdata = json.loads(qpath.read_text(encoding="utf-8"))
                pkg = next((it["package"] for it in qdata.get("items", [])
                            if it.get("slot") == slot and it.get("package")), None)
                if not pkg:
                    raise RuntimeError(f"slot {slot} not in {qpath.name}")
                old_script = script_snapshot(pkg)
                old_prompts = beat_prompts(pkg)
                n = len(mv.narration_segments(pkg, 0))
                beats = [str(b) for b in (pkg.get("beats") or [])]
                prompts = [re.sub(r"\s+", " ", str(p)).strip(" ,.;")[:600]
                           for p in (data.get("prompts") or [])]
                if len(prompts) != n or not all(prompts):
                    prompts = list(old_prompts)   # client view unusable - keep server's
                d = produce_dir(staging_key(queue, slot, pkg))
                if action == "insert":
                    if not (0 <= row <= n - 2):
                        raise RuntimeError("can't insert a beat after the outro")
                    if n >= 20:
                        raise RuntimeError("20 rows per video is the cap")
                    beats.insert(row, NEW_BEAT_TEXT)
                    prompts.insert(row + 1, NEW_PROMPT_TEXT)
                    with _lock:
                        clean_orphan_refs(d, n)
                        for j in range(n, row + 1, -1):       # shift rows >= row+2 up
                            move_beat_refs(d, j, j + 1)
                        shift_ref_choices(d, row + 2, +1)
                    note = f"beat added after row {row + 1}"
                elif action == "remove":
                    if not (1 <= row <= n - 2):
                        raise RuntimeError("only body beats can be deleted (not hook/outro)")
                    if len(beats) <= 3:
                        raise RuntimeError("need at least 3 beats")
                    beats.pop(row - 1)
                    prompts.pop(row)
                    with _lock:
                        clean_orphan_refs(d, n)
                        delete_beat_refs(d, row + 1)
                        for j in range(row + 2, n + 1):       # shift rows > row+1 down
                            move_beat_refs(d, j, j - 1)
                        shift_ref_choices(d, row + 2, -1, drop=row + 1)
                    note = f"beat {row} removed"
                else:
                    raise RuntimeError("action must be insert or remove")
                pkg["beats"] = beats
                qpath.write_text(json.dumps(qdata, indent=2), encoding="utf-8")
                slug = mv.slugify(str(pkg.get("scenarioId", "pkg")))
                if mv.POLISH_CACHE.is_dir():
                    for f in mv.POLISH_CACHE.glob(f"{slug}-*.json"):
                        f.unlink()
                mv._polish_memo.clear()
                save_prompts(pkg, prompts)
                record_history(d, "script", script_snapshot(pkg),
                               baseline=old_script, note=note)
                record_history(d, "prompts", prompts,
                               baseline=old_prompts, note=note)
                self.send_json({"ok": True})
            except Exception as exc:
                self.send_json({"error": str(exc)}, 400)
            return

        if self.path == "/api/produce/revert":
            # Restore a history snapshot. The restore is itself recorded, so
            # nothing is ever lost - you can revert the revert.
            try:
                queue = str(data.get("queue", ""))
                slot = int(data.get("slot") or 0)
                qpath = queue_path(queue)
                if not qpath or not qpath.is_file():
                    raise RuntimeError("queue file not found")
                qdata = json.loads(qpath.read_text(encoding="utf-8"))
                pkg = next((it["package"] for it in qdata.get("items", [])
                            if it.get("slot") == slot and it.get("package")), None)
                if not pkg:
                    raise RuntimeError(f"slot {slot} not in {qpath.name}")
                d = produce_dir(staging_key(queue, slot, pkg))
                h = load_history(d)
                idx = int(data.get("index", -1))
                if not (0 <= idx < len(h)):
                    raise RuntimeError("no such version")
                entry = h[idx]
                if entry.get("kind") == "prompts":
                    save_prompts(pkg, [str(p) for p in (entry.get("data") or [])])
                    record_history(d, "prompts", entry["data"],
                                   note=f"restored from {entry.get('ts', '')}")
                else:
                    snap = entry.get("data") or {}
                    cur_prompts = beat_prompts(pkg)   # preserved when possible
                    if str(snap.get("title", "")).strip():
                        pkg["title"] = str(snap["title"])
                    hooks = list(pkg.get("hooks") or [""])
                    hooks[0] = str(snap.get("hook", "")) or hooks[0]
                    pkg["hooks"] = hooks
                    beats = [str(b) for b in (snap.get("beats") or []) if str(b).strip()]
                    if len(beats) < 3:
                        raise RuntimeError("that version has too few beats to restore")
                    pkg["beats"] = beats
                    if str(snap.get("outro", "")).strip():
                        pkg["outro"] = str(snap["outro"])
                    qpath.write_text(json.dumps(qdata, indent=2), encoding="utf-8")
                    slug = mv.slugify(str(pkg.get("scenarioId", "pkg")))
                    if mv.POLISH_CACHE.is_dir():
                        for f in mv.POLISH_CACHE.glob(f"{slug}-*.json"):
                            f.unlink()
                    mv._polish_memo.clear()
                    if len(cur_prompts) == len(mv.narration_segments(pkg, 0)):
                        save_prompts(pkg, cur_prompts)
                    record_history(d, "script", script_snapshot(pkg),
                                   note=f"restored from {entry.get('ts', '')}")
                self.send_json({"ok": True})
            except Exception as exc:
                self.send_json({"error": str(exc)}, 400)
            return

        if self.path == "/api/produce/enhance-line":
            # AI-rewrite one spoken narration line; nothing is saved here -
            # the client shows the suggestion and only /api/produce/edit
            # (keep) makes it real.
            try:
                queue = str(data.get("queue", ""))
                slot = int(data.get("slot") or 0)
                pkg = load_package(queue, slot)
                index = int(data.get("index") or 0)
                segs = mv.narration_segments(pkg, 0)
                if not (0 <= index < len(segs)):
                    raise RuntimeError("bad line index")
                role = ("hook" if index == 0 else
                        "outro" if index == len(segs) - 1 else f"beat {index}")
                # Ground the rewrite in the beat's SELECTED visual when there
                # is one: the image itself, or the video's first frame.
                img = None
                try:
                    d = produce_dir(staging_key(queue, slot, pkg))
                    choice = mv._ref_choice(d, index + 1)
                    if choice == "image":
                        img = ref_image_path(d, index + 1)
                    elif choice == "video":
                        vid = ref_video_path(d, index + 1)
                        img = video_first_frame(vid) if vid else None
                except Exception:
                    img = None   # a broken frame never blocks a text enhance
                tone = str(data.get("tone") or "punchy")
                # An explicit 🎭 mood rides along; "auto" adds no clause (the
                # tone dropdown already steers the line-level voice).
                mood = str(data.get("mood") or "")
                self.send_json({"ok": True, "grounded": bool(img),
                                "line": enhance_line(pkg.get("title", ""), role,
                                                     segs[index], img=img, tone=tone,
                                                     mood=mood if mood in MOODS else None)})
            except Exception as exc:
                self.send_json({"error": str(exc)}, 400)
            return

        if self.path == "/api/produce/script-from-prompts":
            # Rewrite the WHOLE spoken script from the current visual prompts
            # in the chosen mood, and save it. The prompts are re-pinned right
            # after (a script save normally invalidates them - here they are
            # the source of truth). History records the old script first.
            try:
                queue = str(data.get("queue", ""))
                slot = int(data.get("slot") or 0)
                qpath = queue_path(queue)
                if not qpath or not qpath.is_file():
                    raise RuntimeError("queue file not found")
                qdata = json.loads(qpath.read_text(encoding="utf-8"))
                pkg = next((it["package"] for it in qdata.get("items", [])
                            if it.get("slot") == slot and it.get("package")), None)
                if not pkg:
                    raise RuntimeError(f"slot {slot} not in {qpath.name}")
                mood = resolve_mood(str(data.get("mood") or ""), pkg)
                # Trailer moods can GROW the script to the Clips count - the
                # story is re-told across more scenes for a fuller arc.
                try:
                    clips = max(0, min(20, int(data.get("clips") or 0)))
                except (TypeError, ValueError):
                    clips = 0
                old_script = script_snapshot(pkg)
                prompts = beat_prompts(pkg)
                script = script_from_prompts(pkg, mood, target_rows=clips)
                hooks = list(pkg.get("hooks") or [""])
                hooks[0] = script["hook"]
                pkg["hooks"], pkg["beats"], pkg["outro"] = hooks, script["beats"], script["outro"]
                # A rewrite that names characters replaces the cast; one that
                # doesn't keeps whatever the package already knew.
                if script.get("cast"):
                    pkg["cast"] = script["cast"]
                qpath.write_text(json.dumps(qdata, indent=2), encoding="utf-8")
                # Same row count: the prompts the script was fitted to survive.
                # A grown script has NEW scenes - prompts re-derive from the
                # beats instead (edit them or hit 🎬 Prompts from script after).
                if len(mv.narration_segments(pkg, 0)) == len(prompts):
                    save_prompts(pkg, prompts)
                try:
                    d = produce_dir(staging_key(queue, slot, pkg))
                    record_history(d, "script", script_snapshot(pkg), baseline=old_script,
                                   note=f"written from prompts ({mood})")
                except Exception:
                    pass   # history must never block a save
                self.send_json({"ok": True})
            except Exception as exc:
                self.send_json({"error": str(exc)}, 400)
            return

        if self.path == "/api/produce/prompts-from-script":
            # Rewrite every visual prompt from the current script in the
            # chosen mood, and save them (same store as Save prompts).
            try:
                queue = str(data.get("queue", ""))
                slot = int(data.get("slot") or 0)
                pkg = load_package(queue, slot)
                mood = resolve_mood(str(data.get("mood") or ""), pkg)
                old_prompts = beat_prompts(pkg)
                prompts = prompts_from_script(pkg, mood)
                save_prompts(pkg, prompts)
                try:
                    record_history(produce_dir(staging_key(queue, slot, pkg)),
                                   "prompts", prompts, baseline=old_prompts,
                                   note=f"written from script ({mood})")
                except Exception:
                    pass   # history must never block a save
                self.send_json({"ok": True, "prompts": beat_prompts(pkg)})
            except Exception as exc:
                self.send_json({"error": str(exc)}, 400)
            return

        if self.path == "/api/produce/prompts":
            # Save edited visual prompts (cores, no style suffix).
            try:
                queue = str(data.get("queue", ""))
                slot = int(data.get("slot") or 0)
                pkg = load_package(queue, slot)
                prompts = [re.sub(r"\s+", " ", str(p)).strip(" ,.;")[:600]
                           for p in (data.get("prompts") or [])]
                old_prompts = beat_prompts(pkg)
                save_prompts(pkg, prompts)
                if prompts != old_prompts:
                    try:
                        record_history(produce_dir(staging_key(queue, slot, pkg)),
                                       "prompts", prompts, baseline=old_prompts)
                    except Exception:
                        pass   # history must never block a save
                self.send_json({"ok": True, "prompts": beat_prompts(pkg)})
            except Exception as exc:
                self.send_json({"error": str(exc)}, 400)
            return

        if self.path == "/api/produce/render":
            try:
                qpath = queue_path(str(data.get("queue", "")))
                if not qpath or not qpath.is_file():
                    raise RuntimeError("queue file not found")
                queue = f"exports/{qpath.name}" if qpath.parent == EXPORTS_DIR else qpath.name
                slot = int(data.get("slot") or 0)
                pkg = load_package(queue, slot)
                d = produce_dir(staging_key(queue, slot, pkg))
                # AI modes generate their own visuals - otherwise at least one
                # beat needs a video or an attached image (legacy staged
                # clips still count).
                if (not data.get("infer") and not data.get("ai_visuals")
                        and not data.get("infer_images") and not staged_clips(d)
                        and not any(d.glob("refv-*.mp4"))
                        and not any(ref_image_path(d, i) for i in range(1, 21))):
                    raise RuntimeError("no clips or images on any beat - import from "
                                       "Downloads or attach media to the beats first")
                start_render(queue, slot, d, data)
                self.send_json({"ok": True})
            except Exception as exc:
                self.send_json({"error": str(exc)}, 400)
            return

        if self.path == "/api/morning/run":
            # Manual trigger from the Produce page - drafts a fresh batch of the
            # requested kind right now (on top of today's, if it already ran).
            # Kept OUTSIDE the state lock: the AI calls take a while and have
            # their own batch lock.
            kind = str(data.get("kind") or "scary")
            if kind not in BATCHES:
                self.send_json({"error": "unknown batch kind"}, 400)
                return
            # `clips` = total rows (hook + beats + outro); the writer gets
            # clips-2 beats. Clamped so the arc stays tellable.
            try:
                beats = max(3, min(18, int(data.get("clips") or 7) - 2))
            except (TypeError, ValueError):
                beats = 5
            try:
                self.send_json(batch_run(kind, force=True, beats=beats))
            except Exception as exc:
                self.send_json({"error": str(exc)}, 500)
            return

        if self.path == "/api/produce/draft-idea":
            # 💡 Draft ONE package from the creator's own summary/details:
            # title (invented unless supplied), script, and prompts, honoring
            # the Clips count and 🎭 mood. Outside the state lock - AI calls
            # take a while.
            try:
                idea = re.sub(r"\s+", " ", str(data.get("idea", ""))).strip()[:1500]
                if len(idea) < 12:
                    raise RuntimeError("give the writer a little more - a sentence or two about the idea")
                kind = str(data.get("kind") or "scary")
                if kind not in IDEA_KINDS:
                    raise RuntimeError("unknown kind")
                # Same styling as the batch kind, but idea drafts carry their
                # own scenario prefix so caches/exports are recognizably yours.
                conf = dict(IDEA_KINDS[kind])
                conf["prefix"] = "idea"
                mood = str(data.get("mood") or "")
                mood = mood if mood in MOODS else None   # Auto = the category's own register
                try:
                    clips = max(5, min(20, int(data.get("clips") or 7)))
                except (TypeError, ValueError):
                    clips = 7
                # Dialogue-only trailers have no spoken outro and their hook
                # is the first character line - ask for `clips` beats and
                # redistribute; everything else is hook + beats + outro.
                beats = clips if mood == "trailer" else max(3, min(18, clips - 2))
                title = re.sub(r"\s+", " ", str(data.get("title", ""))).strip()[:120] \
                    or title_from_idea(idea, conf["category"])
                draft = ai_draft(title, conf["category"], conf["runtime"], beats,
                                 idea=idea, mood=mood)
                pkg = scaffold_batch_package(conf, title, draft, conf["runtime"])
                if mood == "trailer":
                    pkg["hooks"] = [pkg["beats"][0]]
                    pkg["beats"] = pkg["beats"][1:]
                    pkg["outro"] = ""
                file = write_package_export(pkg, "idea", title)
                self.send_json({"ok": True, "file": file, "slot": 1, "title": title})
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

            if self.path == "/api/uploaded":
                # Track which videos were actually posted (toggle, with the
                # date it was marked).
                name = safe_name(data.get("name", ""))
                if name:
                    up = state.setdefault("uploaded", {})
                    if data.get("uploaded"):
                        up[name] = int(time.time())
                    else:
                        up.pop(name, None)
                    save_state(state)
                    self.send_json({"ok": True, "uploaded": up.get(name)})
                else:
                    self.send_json({"error": "bad name"}, 400)
                return

            if self.path == "/api/results":
                # Log (or clear) one platform's numbers for a posted video.
                name = safe_name(data.get("video", ""))
                platform = data.get("platform")
                if not name or not (OUTPUT / name).is_file() or platform not in RESULT_PLATFORMS:
                    self.send_json({"error": "unknown video or platform"}, 400)
                    return

                def _num(x):
                    try:
                        return max(0, int(float(str(x).replace(",", ""))))
                    except Exception:
                        return None
                views, likes = _num(data.get("views")), _num(data.get("likes"))
                results = load_results()
                entry = results.setdefault(name, {})
                if views is None and likes is None:
                    entry.pop(platform, None)
                    if not entry:
                        results.pop(name, None)
                else:
                    rec = {"ts": int(time.time())}
                    if views is not None:
                        rec["views"] = views
                    if likes is not None:
                        rec["likes"] = likes
                    entry[platform] = rec
                save_results(results)
                self.send_json({"ok": True, "stats": results.get(name, {})})
                return

            if self.path == "/api/delete":
                name = safe_name(data.get("name", ""))
                src = (OUTPUT / name) if name else None
                if not src or not src.is_file() or src.suffix != ".mp4":
                    self.send_json({"error": "not found"}, 404)
                    return
                TRASH.mkdir(parents=True, exist_ok=True)
                moved = []
                for sib in (src, OUTPUT / f"{src.stem}-thumb.jpg", OUTPUT / f"{src.stem}-post.txt",
                            OUTPUT / f"{src.stem}-meta.json"):
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
    threading.Thread(target=morning_loop, daemon=True).start()
    armed = ", ".join(f"{c['count']}x{c['runtime']}s {c['label']} "
                      f"({'daily after %d:00' % MORNING_HOUR if c['daily'] else 'on demand'})"
                      for c in BATCHES.values())
    print(f"Draft batches armed: {armed} (while running)")
    if args.open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
