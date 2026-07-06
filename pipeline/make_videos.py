#!/usr/bin/env python3
"""
What If Studio - companion video pipeline.

Turns a queue export from the app (whatifstudio-queue.json) into finished
vertical videos: AI voiceover (Microsoft neural voices via edge-tts),
per-beat visuals, and modern word-by-word "pop" captions, rendered with
ffmpeg.

This tool is OPTIONAL and lives alongside the static app. The app itself
never requires it. Nothing here posts anywhere - you review and upload
your own videos.

Usage:
    python make_videos.py whatifstudio-queue.json
    python make_videos.py package.json --hook 2
    python make_videos.py queue.json --backgrounds backgrounds --music music

Visuals: drop clips/images in the backgrounds folder. If there are several,
each script beat gets its own clip in order (great for "one example per
beat" videos). With one file it is used throughout; with none, an animated
gradient in the scenario's colors is generated.

Requirements: Python 3.9+, `pip install -r requirements.txt`, ffmpeg on PATH
(auto-detected if installed via winget). edge-tts needs internet.
"""

import argparse
import asyncio
import glob
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import edge_tts
except ImportError:
    sys.exit("edge-tts is not installed. Run:  python -m pip install --user -r requirements.txt")

# ---------------------------------------------------------------- constants

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".ogg", ".flac"}

WIDTH, HEIGHT, FPS = 1080, 1920, 30
ASSETS = Path(__file__).resolve().parent / "assets"
CAPTION_FONT_FILE = ASSETS / "Poppins-ExtraBold.ttf"
CAPTION_FONT_NAME = "Poppins ExtraBold"

# App voice style -> edge-tts voice + delivery tweaks
VOICE_MAP = {
    "Calm Narrator":            {"voice": "en-US-ChristopherNeural", "rate": "-5%",  "pitch": "-2Hz"},
    "High-Energy Storyteller":  {"voice": "en-US-GuyNeural",         "rate": "+12%", "pitch": "+2Hz"},
    "Deadpan Documentarian":    {"voice": "en-US-EricNeural",        "rate": "-8%",  "pitch": "-4Hz"},
}
DEFAULT_VOICE = {"voice": "en-US-ChristopherNeural", "rate": "+0%", "pitch": "+0Hz"}

# Scenario category -> music mood folder under music/
MOOD_BY_CATEGORY = {
    "Scary/Weird": "eerie",
    "Internet Mystery": "tense",
    "Unsettling Everyday": "tense",
    "Alternate Reality": "wonder",
    "Science": "wonder",
    "Speculative": "wonder",
    "History": "wonder",
    "Pop Culture": "upbeat",
}
MUSIC_VOLUME = 0.12

# Free AI image generation (Pollinations - no account, no key).
# Each style is a prompt suffix appended to the scenario's shot description.
AI_STYLES = {
    "cinematic":   "vertical cinematic digital art, dramatic lighting, rich colors, high detail, no text, no words, no letters",
    "3d":          "soft 3d pixar style render, cinematic lighting, expressive characters, high detail, no text, no words, no letters",
    "infographic": "flat design vector illustration, corporate infographic style, soft pastel beige background, simple geometric shapes and characters, clean minimal composition, no text, no words, no letters",
    "dark":        "moody dark atmospheric illustration, deep shadows, single strong light source, eerie but tasteful, high detail, no text, no words, no letters",
}
AI_IMAGE_HOST = "https://image.pollinations.ai/prompt/"

# Modern caption look (ASS): white words, spoken word pops to yellow.
CAP_WHITE = r"&H00FFFFFF&"
CAP_HL = r"&H0000D4FF&"      # bright yellow (ASS is &HAABBGGRR)
CAP_FONTSIZE = 92
CAP_MAX_WORDS = 3           # words visible per phrase
CAP_Y = 1200                # caption anchor (of 1920) - lower third

TITLE_SECONDS = 2.2         # title card hold at the top of the video
CTA_SECONDS = 2.6           # closing follow-card during the outro
XFADE_DUR = 0.25            # crossfade length between beat clips

# ---------------------------------------------------------------- helpers


def find_tool(name):
    """Locate ffmpeg/ffprobe on PATH or in the winget install directory."""
    path = shutil.which(name)
    if path:
        return path
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        hits = glob.glob(os.path.join(
            local, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "**", "bin", f"{name}.exe"
        ), recursive=True)
        if hits:
            return hits[0]
    sys.exit(f"{name} not found. Install it (winget install Gyan.FFmpeg) or add it to PATH.")


def run(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("ffmpeg/ffprobe failed:\n" + (result.stderr or result.stdout)[-1500:])
    return result


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "package"


def clean_for_tts(text):
    """Strip emoji/symbols the voice would mangle; keep normal punctuation."""
    text = re.sub(r"[\U0001F000-\U0001FAFF←-⇿☀-➿️]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def narration_segments(pkg, hook_index):
    """Ordered spoken segments: [hook, *beats, outro] (non-empty, cleaned)."""
    hooks = pkg.get("hooks", [])
    hook = hooks[min(hook_index, len(hooks) - 1)] if hooks else ""
    raw = [hook] + list(pkg.get("beats", [])) + [pkg.get("outro", "")]
    return [clean_for_tts(p) for p in raw if p and p.strip()]


def hex_to_ffmpeg(color, fallback):
    if isinstance(color, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        return "0x" + color[1:]
    return fallback


def pick_file(directory, exts):
    folder = Path(directory) if directory else None
    if not folder or not folder.is_dir():
        return None
    files = sorted(f for f in folder.iterdir() if f.suffix.lower() in exts)
    return random.choice(files) if files else None


def pick_music(pkg, music_dir):
    """Pick a track matching the scenario's mood; fall back to loose files."""
    root = Path(music_dir) if music_dir else None
    if not root or not root.is_dir():
        return None
    mood = MOOD_BY_CATEGORY.get(pkg.get("category", ""), "wonder")
    return pick_file(root / mood, AUDIO_EXTS) or pick_file(root, AUDIO_EXTS)


def music_credit_for(music, music_dir):
    """Look up the license credit line for a track (written by get_music.py)."""
    if not music:
        return None
    try:
        credits = json.loads((Path(music_dir) / "credits.json").read_text(encoding="utf-8"))
        return credits.get(music.name)
    except Exception:
        return None


def list_visuals(directory):
    folder = Path(directory) if directory else None
    if not folder or not folder.is_dir():
        return []
    return sorted(f for f in folder.iterdir() if f.suffix.lower() in (VIDEO_EXTS | IMAGE_EXTS))


# ---------------------------------------------------------------- TTS + captions


async def synthesize(text, vconf, mp3_path):
    """Generate speech and collect per-word timings (needs WordBoundary)."""
    communicate = edge_tts.Communicate(text, vconf["voice"], rate=vconf["rate"], pitch=vconf["pitch"],
                                       boundary="WordBoundary")
    words = []
    with open(mp3_path, "wb") as out:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                out.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                end = start + chunk["duration"] / 1e7
                words.append((start, end, chunk["text"]))
    if not words:
        raise RuntimeError("TTS returned no word timings - cannot build synced captions.")
    return words


# ---------------------------------------------------------------- ElevenLabs voice (optional, paid)

ELEVENLABS_API = "https://api.elevenlabs.io/v1"

# App voice style -> preferred ElevenLabs premade voices, by name (first match wins).
ELEVENLABS_VOICE_BY_STYLE = {
    "Calm Narrator":           ["Adam", "Brian", "Rachel", "Daniel"],
    "High-Energy Storyteller": ["Josh", "Antoni", "Callum", "Charlie"],
    "Deadpan Documentarian":   ["Arnold", "Clyde", "George", "Bill"],
}


def elevenlabs_key():
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if key:
        return key
    f = Path(__file__).resolve().parent / "elevenlabs_key.txt"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    return None


def elevenlabs_voices(key):
    """{name: voice_id} for every voice on the account (premade + cloned)."""
    req = urllib.request.Request(f"{ELEVENLABS_API}/voices",
                                 headers={"xi-api-key": key, "User-Agent": "WhatIfStudio-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return {v["name"]: v["voice_id"] for v in data.get("voices", []) if v.get("voice_id")}


def _voice_base(name):
    """'Adam - Dominant, Firm' -> 'adam' (accounts often carry descriptive suffixes)."""
    return name.split(" - ")[0].strip().lower()


def pick_elevenlabs_voice(style, override, key):
    """Resolve a voice: explicit override (name or raw id) beats style mapping."""
    voices = elevenlabs_voices(key)
    if override:
        want = override.strip().lower()
        for name, vid in voices.items():
            if name.lower() == want or _voice_base(name) == want:
                return vid, name
        return override, override      # assume the user passed a raw voice id
    for wanted in ELEVENLABS_VOICE_BY_STYLE.get(style, []):
        for name, vid in voices.items():
            if _voice_base(name) == wanted.lower():
                return vid, name
    if voices:
        name = sorted(voices)[0]
        return voices[name], name
    raise RuntimeError("no voices available on this ElevenLabs account")


def chars_to_words(chars, starts, ends):
    """Group ElevenLabs character-level timestamps into (start, end, word)."""
    words, cur, w_start, w_end = [], "", None, None
    for ch, s, e in zip(chars, starts, ends):
        if str(ch).isspace():
            if cur:
                words.append((w_start, w_end, cur))
                cur = ""
        else:
            if not cur:
                w_start = s
            cur += str(ch)
            w_end = e
    if cur:
        words.append((w_start, w_end, cur))
    return words


def synthesize_elevenlabs(text, voice_id, model, mp3_path, key):
    """ElevenLabs TTS with character timestamps -> mp3 + per-word timings,
    matching the edge-tts word format so captions/charts work unchanged."""
    import base64
    url = f"{ELEVENLABS_API}/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128"
    body = json.dumps({
        "text": text,
        "model_id": model,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "xi-api-key": key,
        "Content-Type": "application/json",
        "User-Agent": "WhatIfStudio-pipeline/1.0",
    })
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    audio = data.get("audio_base64")
    align = data.get("alignment") or data.get("normalized_alignment")
    if not audio or not align:
        raise RuntimeError("ElevenLabs response missing audio or alignment:\n" + json.dumps(data)[:400])
    Path(mp3_path).write_bytes(base64.b64decode(audio))
    words = chars_to_words(align.get("characters", []),
                           align.get("character_start_times_seconds", []),
                           align.get("character_end_times_seconds", []))
    if not words:
        raise RuntimeError("ElevenLabs alignment produced no word timings")
    return words


def ass_time(seconds):
    cs = max(0, int(round(seconds * 100)))
    h = cs // 360000
    m = cs % 360000 // 6000
    s = cs % 6000 // 100
    c = cs % 100
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def group_phrases(words, max_words=CAP_MAX_WORDS, max_gap=0.55):
    phrases, cur = [], []
    for start, end, word in words:
        if cur:
            prev_end = cur[-1][1]
            sentence_break = cur[-1][2].rstrip('"”’').endswith((".", "!", "?", ":", ","))
            if len(cur) >= max_words or (start - prev_end) > max_gap or sentence_break:
                phrases.append(cur)
                cur = []
        cur.append((start, end, word))
    if cur:
        phrases.append(cur)
    return phrases


def sanitize_card_text(text):
    """Card text: plain uppercase, no emoji, safe for ASS dialogue."""
    text = re.sub(r"[\U0001F000-\U0001FAFF←-⇿☀-➿️]", "", str(text))
    return re.sub(r"\s+", " ", text).strip().upper()


def words_to_ass(words, pkg=None, total=None):
    """Modern captions: short phrases; the spoken word pops yellow + scales.
    Also lays a title card over the hook and a follow-card over the outro."""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 1
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{CAPTION_FONT_NAME},{CAP_FONTSIZE},{CAP_WHITE},{CAP_WHITE},&H00101010,&H90000000,0,0,0,0,100,100,1,0,1,7,2,5,60,60,0,1
Style: Title,{CAPTION_FONT_NAME},112,{CAP_HL},{CAP_HL},&H00101010,&H90000000,0,0,0,0,100,100,1,0,1,9,3,8,70,70,360,1
Style: CTA,{CAPTION_FONT_NAME},62,{CAP_WHITE},{CAP_WHITE},&H00101010,&H90000000,0,0,0,0,100,100,1,0,1,6,2,8,90,90,430,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Flatten to one caption event per word so we can butt each event exactly
    # against the next (no overlap, no gap -> no doubled/garbled frames).
    events = []
    for phrase in group_phrases(words):
        for k, (start, _, _) in enumerate(phrase):
            parts = []
            for j, (_, _, w) in enumerate(phrase):
                token = w.upper()
                parts.append(f"{{\\c{CAP_HL}}}{token}{{\\c{CAP_WHITE}}}" if j == k else token)
            tags = f"\\an5\\pos({WIDTH // 2},{CAP_Y})"
            if k == 0:  # entrance pop only when a new phrase appears
                tags += "\\fad(70,0)\\fscx78\\fscy78\\t(0,120,\\fscx100\\fscy100)"
            events.append([start, f"{{{tags}}}" + " ".join(parts)])

    lines = []
    for i, (start, text) in enumerate(events):
        end = events[i + 1][0] if i + 1 < len(events) else start + 0.6
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Cap,,0,0,0,,{text}")

    if pkg:
        title = sanitize_card_text((pkg.get("thumbnails") or [pkg.get("title", "")])[0])
        if title:
            fx = r"{\fad(120,200)\fscx80\fscy80\t(0,150,\fscx100\fscy100)}"
            lines.append(f"Dialogue: 1,{ass_time(0)},{ass_time(TITLE_SECONDS)},Title,,0,0,0,,{fx}{title}")
    if total and total > 12:
        cta_start = max(0.0, total - CTA_SECONDS)
        fx = r"{\fad(250,0)}"
        lines.append(f"Dialogue: 1,{ass_time(cta_start)},{ass_time(total + 0.3)},CTA,,0,0,0,,{fx}FOLLOW FOR THE NEXT WHAT-IF")

    return header + "\n".join(lines) + "\n"


# ---------------------------------------------------------------- AI visuals


def ai_prompt_for_segment(pkg, seg_index, seg_count, style_suffix):
    """Build an image prompt for one narration segment from the shot list."""
    shots = pkg.get("shotList") or [pkg.get("premise", pkg.get("title", "abstract scene"))]
    pick = min(round(seg_index * (len(shots) - 1) / max(1, seg_count - 1)), len(shots) - 1)
    src = shots[pick]
    src = re.sub(r"^[A-Za-z /-]{2,20}:", "", src)                      # "Hook:" style prefixes
    src = re.sub(r"[\"“”‘’']", "", src)
    # Drop instructions about on-screen text - generated text comes out garbled.
    src = re.sub(r"\b(labeled|labelled|stamped|caption|chyron|lower.third|overlay|typed|on.screen text)\b[^,.;]*",
                 "", src, flags=re.I)
    src = re.sub(r"\s+", " ", src).strip(" ,.;-")
    return f"{src}, {style_suffix}"


def fetch_ai_image(prompt, dest, seed):
    url = (AI_IMAGE_HOST + urllib.parse.quote(prompt)
           + f"?width={WIDTH}&height={HEIGHT}&nologo=true&seed={seed}")
    req = urllib.request.Request(url, headers={"User-Agent": "WhatIfStudio-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=180) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out)
    if dest.stat().st_size < 5000:
        dest.unlink(missing_ok=True)
        raise RuntimeError("image response too small")


def generate_ai_visuals(pkg, seg_count, style_key, cache_root):
    """One generated image per narration segment, cached per scenario+style."""
    suffix = AI_STYLES[style_key]
    folder = Path(cache_root) / f"{pkg.get('scenarioId', 'pkg')}-{style_key}"
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    for i in range(seg_count):
        dest = folder / f"{i + 1:02d}.jpg"
        if not dest.exists():
            prompt = ai_prompt_for_segment(pkg, i, seg_count, suffix)
            for attempt in range(3):
                try:
                    fetch_ai_image(prompt, dest, seed=(i + 1) * 13 + attempt * 101)
                    print(f"    image {i + 1}/{seg_count} generated")
                    break
                except Exception as exc:
                    if attempt == 2:
                        print(f"    image {i + 1}/{seg_count} FAILED ({exc}) - neighbors will fill in")
                    else:
                        time.sleep(3)
        if dest.exists():
            files.append(dest)
    if not files:
        raise RuntimeError("AI visual generation produced no images (network down?)")
    return files


# ---------------------------------------------------------------- stock footage (Pexels)

PEXELS_SEARCH = "https://api.pexels.com/videos/search"
STOCK_STOPWORDS = set((
    "the a an and or but of to in on for with without into over under from that this these those "
    "it its is are was were be been being you your they them their we our us he she his her "
    "what if would could should might will now then here there when where why how not no yes "
    "most some many much more less every each one two three first day year time thing things "
    "actually really just even still only about like than because so up out off down back "
    "picture imagine setup payoff hook beat twist real reality version part"
).split())


def pexels_api_key():
    """Read the free Pexels key from PEXELS_API_KEY or pipeline/pexels_key.txt."""
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if key:
        return key
    f = Path(__file__).resolve().parent / "pexels_key.txt"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    return None


def beat_query(pkg, beat_text):
    """A short, on-topic Pexels search query: scenario anchor + a beat noun."""
    tags = pkg.get("tags") or []
    anchor = tags[0] if tags else ""
    words = [w for w in re.findall(r"[a-zA-Z]{4,}", beat_text.lower()) if w not in STOCK_STOPWORDS]
    picks = list(dict.fromkeys(words))[:2]
    query = " ".join(dict.fromkeys(([anchor] if anchor else []) + picks)).strip()
    return query or anchor or sanitize_card_text(pkg.get("title", "abstract")).lower()


def best_portrait_link(video):
    """Pick a vertical video file, largest height up to 1920."""
    files = [f for f in video.get("video_files", []) if f.get("link")]
    portrait = [f for f in files if f.get("height", 0) >= f.get("width", 1)] or files
    if not portrait:
        return None
    under = sorted((f for f in portrait if f.get("height", 0) <= 1920), key=lambda f: f.get("height", 0))
    if under:
        return under[-1].get("link")
    return sorted(portrait, key=lambda f: f.get("height", 0))[0].get("link")


def pexels_search(query, key, per_page=10):
    url = PEXELS_SEARCH + "?" + urllib.parse.urlencode(
        {"query": query, "orientation": "portrait", "per_page": per_page, "size": "medium"})
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": "WhatIfStudio-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read()).get("videos", [])


def fetch_stock_visuals(pkg, segments, key, cache_root, credits):
    """One Pexels clip per narration segment, cached per scenario.
    Appends contributor names to `credits` for the post kit."""
    folder = Path(cache_root) / slugify(pkg.get("scenarioId", "pkg"))
    folder.mkdir(parents=True, exist_ok=True)
    results, used = [], set()
    for i, seg in enumerate(segments):
        dest = folder / f"{i + 1:02d}.mp4"
        if dest.exists():
            results.append(dest)
            continue
        query = beat_query(pkg, seg)
        try:
            videos = pexels_search(query, key)
        except Exception as exc:
            print(f"    stock search failed ('{query}'): {exc}")
            videos = []
        link, author = None, None
        for v in videos:
            if v.get("id") in used:
                continue
            link = best_portrait_link(v)
            if link:
                used.add(v.get("id"))
                author = (v.get("user") or {}).get("name")
                break
        if not link:
            print(f"    no stock clip for beat {i + 1} ('{query}')")
            continue
        try:
            req = urllib.request.Request(link, headers={"User-Agent": "WhatIfStudio-pipeline/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
                shutil.copyfileobj(resp, out)
            if dest.stat().st_size < 20000:
                dest.unlink(missing_ok=True)
                raise RuntimeError("clip too small")
            if author:
                credits.add(author)
            print(f"    clip {i + 1}/{len(segments)}: '{query}'")
            results.append(dest)
        except Exception as exc:
            print(f"    download failed beat {i + 1}: {exc}")
    if not results:
        raise RuntimeError("no stock clips fetched (check the key and your connection)")
    return results


# ---------------------------------------------------------------- AI video (tryinfer / Reka Infer)

INFER_BASE = "https://api.tryinfer.com/v1"
INFER_POLL_INTERVAL = 8      # seconds between status checks
INFER_POLL_TIMEOUT = 900     # give up on one clip after 15 minutes
VIDEO_MOTION_SUFFIX = "cinematic, subtle natural camera movement, smooth motion, atmospheric, vertical 9:16"
_VIDEO_EXT_RE = re.compile(r"\.(mp4|mov|webm|m4v)(\?|$)", re.I)


def infer_api_key():
    """Read the tryinfer key from TRYINFER_API_KEY / INFER_API_KEY or a file."""
    for var in ("TRYINFER_API_KEY", "INFER_API_KEY"):
        key = os.environ.get(var, "").strip()
        if key:
            return key
    f = Path(__file__).resolve().parent / "tryinfer_key.txt"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    return None


def pollinations_image_url(prompt, seed=7):
    """A public on-demand image URL usable as an image-to-video first frame."""
    return (AI_IMAGE_HOST + urllib.parse.quote(prompt)
            + f"?width={WIDTH}&height={HEIGHT}&nologo=true&seed={seed}")


def infer_submit(model, task, input_obj, key):
    url = f"{INFER_BASE}/inference/{model}/{task}"
    body = json.dumps({"input": input_obj}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "WhatIfStudio-pipeline/1.0",
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    rid = data.get("request_id") or data.get("id") or data.get("requestId")
    if not rid:
        raise RuntimeError(f"submit returned no request_id: {json.dumps(data)[:400]}")
    return rid


def infer_poll(request_id, key):
    req = urllib.request.Request(f"{INFER_BASE}/inference/requests/{request_id}",
                                 headers={"Authorization": f"Bearer {key}",
                                          "User-Agent": "WhatIfStudio-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def _find_status(obj):
    """Find a status string anywhere in the poll response."""
    known = {"COMPLETED", "SUCCEEDED", "SUCCESS", "FAILED", "ERROR", "CANCELLED",
             "CANCELED", "PENDING", "QUEUED", "RUNNING", "IN_PROGRESS", "PROCESSING", "STARTED"}
    if isinstance(obj, dict):
        for key in ("status", "state"):
            v = obj.get(key)
            if isinstance(v, str) and v.upper() in known:
                return v.upper()
        for v in obj.values():
            found = _find_status(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_status(v)
            if found:
                return found
    return None


def _find_video_url(obj):
    """Find the finished video URL anywhere in the poll response."""
    if isinstance(obj, str):
        return obj if obj.startswith("http") and _VIDEO_EXT_RE.search(obj) else None
    if isinstance(obj, dict):
        # Prefer likely keys first.
        for key in ("video_url", "url", "output_url", "download_url", "result_url"):
            v = obj.get(key)
            if isinstance(v, str) and v.startswith("http") and (_VIDEO_EXT_RE.search(v) or key != "url"):
                return v
        for v in obj.values():
            found = _find_video_url(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_video_url(v)
            if found:
                return found
    return None


def _prewarm_url(url):
    """Fetch a generate-on-demand image once so the provider's fetch is fast."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WhatIfStudio-pipeline/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            return len(resp.read()) > 5000
    except Exception:
        return False


def _find_price(obj):
    """Find output.usage.price_usd anywhere in the poll response."""
    if isinstance(obj, dict):
        v = obj.get("price_usd")
        if isinstance(v, (int, float)):
            return float(v)
        for v in obj.values():
            found = _find_price(v)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_price(v)
            if found is not None:
                return found
    return None


def _run_infer_job(model, task, input_obj, key):
    """Submit one job and poll to a terminal state. Returns (url, price, error)."""
    rid = infer_submit(model, task, input_obj, key)
    waited = 0
    while waited < INFER_POLL_TIMEOUT:
        time.sleep(INFER_POLL_INTERVAL)
        waited += INFER_POLL_INTERVAL
        resp = infer_poll(rid, key)
        status = _find_status(resp)
        if status in ("COMPLETED", "SUCCEEDED", "SUCCESS"):
            url = _find_video_url(resp)
            if not url:
                return None, None, "completed but no video URL: " + json.dumps(resp)[:400]
            return url, _find_price(resp), None
        if status in ("FAILED", "ERROR", "CANCELLED", "CANCELED"):
            err = json.dumps((resp or {}).get("error") or resp)[:300]
            return None, None, f"{status}: {err}"
    return None, None, f"timed out after {INFER_POLL_TIMEOUT}s"


def generate_infer_videos(pkg, segments, key, model, task, duration, cache_root):
    """One AI-generated clip per beat via tryinfer. image-to-video animates a
    free Pollinations first frame (shared style = coherence); if the provider
    content-flags that image, the beat falls back to text-to-video. Clips
    cache per scenario+model. Paid API - one billed job per beat."""
    folder = Path(cache_root) / f"{slugify(pkg.get('scenarioId', 'pkg'))}-{model}"
    folder.mkdir(parents=True, exist_ok=True)
    files, spent = [], 0.0
    for i, seg in enumerate(segments):
        dest = folder / f"{i + 1:02d}.mp4"
        if dest.exists():
            files.append(dest)
            continue
        motion = ai_prompt_for_segment(pkg, i, len(segments), VIDEO_MOTION_SUFFIX)
        base_input = {"prompt": motion, "duration_seconds": str(duration), "aspect_ratio": "9:16"}

        attempts = []
        if task == "image-to-video":
            frame_prompt = ai_prompt_for_segment(pkg, i, len(segments), AI_STYLES["cinematic"])
            image_url = pollinations_image_url(frame_prompt, seed=(i + 1) * 17)
            if _prewarm_url(image_url):
                attempts.append(("image-to-video", {**base_input, "image_url": image_url}))
            else:
                print(f"    beat {i + 1}: first-frame image unavailable, using text-to-video")
        attempts.append(("text-to-video", dict(base_input)))

        url = None
        for attempt_task, input_obj in attempts:
            try:
                url, price, err = _run_infer_job(model, attempt_task, input_obj, key)
            except Exception as exc:
                url, price, err = None, None, str(exc)
            if url:
                spent += price or 0.0
                price_note = f" (${price:.2f})" if price is not None else ""
                print(f"    beat {i + 1}/{len(segments)}: done via {attempt_task}{price_note}")
                break
            print(f"    beat {i + 1}/{len(segments)} {attempt_task} failed: {err}")

        if not url:
            continue
        try:
            dl = urllib.request.Request(url, headers={"User-Agent": "WhatIfStudio-pipeline/1.0"})
            with urllib.request.urlopen(dl, timeout=180) as resp, open(dest, "wb") as out:
                shutil.copyfileobj(resp, out)
            if dest.stat().st_size < 20000:
                dest.unlink(missing_ok=True)
                raise RuntimeError("downloaded clip too small")
            files.append(dest)
        except Exception as exc:
            print(f"    beat {i + 1}/{len(segments)} download failed: {exc}")
    print(f"    AI-video spend this run: ${spent:.2f}")
    if not files:
        raise RuntimeError("no AI video clips produced (check key, model name, and credits)")
    return files


# ---------------------------------------------------------------- visuals


def probe_duration(ffprobe, media_path):
    out = run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(media_path)])
    return float(out.stdout.strip())


def segment_spans(segments, words, total):
    """Map each spoken segment to a (start, end) time span using word counts."""
    counts = [max(1, len(clean_for_tts(s).split())) for s in segments]
    boundaries, cum = [0], 0
    for c in counts:
        cum += c
        boundaries.append(min(cum, len(words)))
    spans = []
    for i in range(len(segments)):
        wi_s, wi_e = boundaries[i], boundaries[i + 1]
        start = 0.0 if i == 0 else (words[wi_s][0] if wi_s < len(words) else total)
        end = total if i == len(segments) - 1 else (words[wi_e][0] if wi_e < len(words) else total)
        if end <= start:
            end = start + 0.5
        spans.append((start, end))
    return spans


CHART_ANIM = 1.4  # seconds to count up


def detect_chart(beat_text):
    """Return an animated-chart spec for the headline number in a beat, or None.
    Kept conservative: one graphic per beat, only for clear, punchy numbers."""
    t = beat_text
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent\b)", t, re.I)
    if m:
        pct = float(m.group(1))
        if 1 <= pct <= 100:
            return {"kind": "bar", "target": int(round(pct)), "prefix": "", "suffix": "PERCENT", "pct": pct}
    m = re.search(r"(\$)?\s*(\d[\d,]*(?:\.\d+)?)\s*(trillion|billion|million|thousand)\b", t, re.I)
    if m:
        coeff = float(m.group(2).replace(",", ""))
        if coeff >= 1:
            return {"kind": "counter", "target": int(round(coeff)),
                    "prefix": "$" if m.group(1) else "", "suffix": m.group(3).upper()}
    m = re.search(r"\$\s*(\d[\d,]*)\b", t)
    if m:
        return {"kind": "counter", "target": int(m.group(1).replace(",", "")), "prefix": "$", "suffix": ""}
    m = re.search(r"\b(\d[\d,]*)\s*(days?|years?|hours?|minutes?|seconds?|kilometres?|kilometers?|km|miles?|metres?|meters?|degrees?)\b", t, re.I)
    if m:
        val = int(m.group(1).replace(",", ""))
        if 2 <= val <= 100000:
            return {"kind": "counter", "target": val, "prefix": "", "suffix": m.group(2).upper()}
    for m in re.finditer(r"\b(\d[\d,]{3,})\b", t):
        digits = m.group(1).replace(",", "")
        val = int(digits)
        if len(digits) == 4 and 1000 <= val <= 2099:
            continue  # looks like a year - a counter ticking up a year reads badly
        return {"kind": "counter", "target": val, "prefix": "", "suffix": ""}
    return None


def chart_overlay_vf(spec, duration, font_ff):
    """ffmpeg filter fragment: a counter that ticks up (+ a bar for percentages)."""
    anim = min(CHART_ANIM, max(0.6, duration * 0.7))
    tgt = spec["target"]
    count = f"%{{eif\\:min({tgt}\\,{tgt}*t/{anim})\\:d}}"
    number = spec["prefix"] + count
    parts = [
        f"drawtext=fontfile={font_ff}:text='{number}':fontsize=210:fontcolor=white:"
        f"borderw=10:bordercolor=black:x=(w-tw)/2:y=420"
    ]
    if spec["suffix"]:
        parts.append(
            f"drawtext=fontfile={font_ff}:text='{spec['suffix']}':fontsize=78:fontcolor=0xF5C400:"
            f"borderw=6:bordercolor=black:x=(w-tw)/2:y=690"
        )
    if spec["kind"] == "bar":
        trackw, barh, bary = 760, 44, 830
        trackx = (WIDTH - trackw) // 2
        frac = spec["pct"] / 100.0
        parts.append(f"drawbox=x={trackx}:y={bary}:w={trackw}:h={barh}:color=0x333333@0.85:t=fill")
        parts.append(f"drawbox=x={trackx}:y={bary}:w='{trackw}*{frac:.4f}*min(1\\,t/{anim})':h={barh}:color=0xF5C400:t=fill")
    return ",".join(parts)


def render_segment_clip(ffmpeg, visual, duration, out_path, index=0, chart=None, font_ff=None, cwd=None):
    """Scale/crop one visual to a full-frame vertical clip of the given length.
    Still images get an alternating camera move (in / pan / out / pan back).
    If a chart spec is given, an animated counter/bar is overlaid.
    `cwd` lets the chart drawtext reference the font by bare filename, avoiding
    the Windows drive-letter colon that breaks ffmpeg's filtergraph parser."""
    base = (f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS}")
    if visual.suffix.lower() in IMAGE_EXTS:
        loop = ["-loop", "1"]
        frames = int(duration * FPS) + 1
        center = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        moves = [
            f"zoompan=z='min(zoom+0.0006,1.10)':{center}",                          # slow push in
            f"zoompan=z=1.08:x='(iw-iw/zoom)*on/{frames}':y='ih/2-(ih/zoom/2)'",    # drift right
            f"zoompan=z='max(1.001,1.10-0.0007*on)':{center}",                      # pull back
            f"zoompan=z=1.08:x='(iw-iw/zoom)*(1-on/{frames})':y='ih/2-(ih/zoom/2)'",# drift left
        ]
        vf = base + "," + moves[index % len(moves)] + f":d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS}"
    else:
        loop = ["-stream_loop", "-1"]
        vf = base
    if chart and font_ff:
        vf += "," + chart_overlay_vf(chart, duration, font_ff)
    run([ffmpeg, "-y", *loop, "-i", str(Path(visual).resolve()), "-t", f"{duration:.2f}", "-vf", vf, "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out_path)], cwd=cwd)


def build_clip_base(ffmpeg, visuals, spans, tmp, charts=None, font_ff=None):
    """One clip per beat with alternating motion, joined by crossfades.
    Segments before the last are rendered XFADE_DUR longer so the fades
    consume the extra tail and the visual timeline stays in sync with audio.
    `charts` (aligned to spans) overlays an animated number on chart beats."""
    durs = [round(max(0.4, end - start), 2) for start, end in spans]
    seg_files = []
    for i, dur in enumerate(durs):
        seg = tmp / f"seg_{i:02d}.mp4"
        extra = XFADE_DUR if i < len(durs) - 1 else 0.5
        chart = charts[i] if charts and i < len(charts) else None
        render_segment_clip(ffmpeg, visuals[i % len(visuals)], dur + extra, seg, index=i,
                            chart=chart, font_ff=font_ff, cwd=tmp)
        seg_files.append(seg)

    if len(seg_files) == 1:
        return seg_files[0]

    inputs = []
    for f in seg_files:
        inputs += ["-i", f.name]
    chain = []
    prev = "[0:v]"
    offset = 0.0
    for i in range(1, len(seg_files)):
        offset += durs[i - 1]
        label = f"[x{i}]"
        chain.append(f"{prev}[{i}:v]xfade=transition=fade:duration={XFADE_DUR}:offset={offset:.2f}{label}")
        prev = label
    run([ffmpeg, "-y", *inputs, "-filter_complex", ";".join(chain), "-map", prev,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "base.mp4"], cwd=tmp)
    return tmp / "base.mp4"


def esc_drawtext(text):
    """Uppercase card text made safe for an ffmpeg drawtext value."""
    text = sanitize_card_text(text)
    text = text.replace("\\", "").replace("'", "").replace('"', "").replace("%", "")
    return text.replace(":", "\\:")


def wrap_title(text, max_chars=16):
    """Split a cover title into at most two balanced lines."""
    text = sanitize_card_text(text)
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    best, best_diff = None, 10 ** 9
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        if abs(len(a) - len(b)) < best_diff:
            best_diff, best = abs(len(a) - len(b)), (a, b)
    return list(best) if best else [text]


def render_thumbnail(ffmpeg, visual, pkg, out_path, tmp, font_ff):
    """Save a clean cover image: the first visual + the title-card text,
    with no captions or counters. Ready to upload as the video's thumbnail."""
    lines = wrap_title((pkg.get("thumbnails") or [pkg.get("title", "")])[0])
    fontsize = 128 if len(lines) == 1 else 106
    line_h = fontsize + 22

    if visual and visual.suffix.lower() in (IMAGE_EXTS | VIDEO_EXTS):
        # For a video, -frames:v 1 grabs the first frame as the cover.
        inp = ["-i", str(Path(visual).resolve())]
        pre = (f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
               f"crop={WIDTH}:{HEIGHT},setsar=1")
    else:
        colors = pkg.get("colors") or {}
        c0 = hex_to_ffmpeg(colors.get("from"), "0x151a30")
        c1 = hex_to_ffmpeg(colors.get("to"), "0x6a5ae0")
        inp = ["-f", "lavfi", "-i", f"gradients=s={WIDTH}x{HEIGHT}:c0={c0}:c1={c1}"]
        pre = "null"

    band_h = line_h * len(lines) + 90
    band_y = HEIGHT // 2 - band_h // 2
    filters = [pre, f"drawbox=x=0:y={band_y}:w={WIDTH}:h={band_h}:color=black@0.45:t=fill"]
    start_y = HEIGHT // 2 - (line_h * len(lines)) // 2 + 6
    for i, ln in enumerate(lines):
        filters.append(
            f"drawtext=fontfile={font_ff}:text='{esc_drawtext(ln)}':fontsize={fontsize}:"
            f"fontcolor=0xF5C400:borderw=9:bordercolor=black:x=(w-tw)/2:y={start_y + i * line_h}"
        )
    run([ffmpeg, "-y", *inp, "-frames:v", "1", "-vf", ",".join(filters), "-q:v", "3",
         str(out_path)], cwd=tmp)


def final_render(ffmpeg, base, pkg, total, has_music, out_path, tmp):
    """Overlay captions and mix audio onto the base video (or a gradient)."""
    if base is not None:
        video_in = ["-i", base.name]
    else:
        colors = pkg.get("colors") or {}
        c0 = hex_to_ffmpeg(colors.get("from"), "0x151a30")
        c1 = hex_to_ffmpeg(colors.get("to"), "0x6a5ae0")
        video_in = ["-f", "lavfi", "-i",
                    f"gradients=s={WIDTH}x{HEIGHT}:c0={c0}:c1={c1}:speed=0.012:rate={FPS}"]

    inputs = [*video_in, "-i", "voice.mp3"]
    filters = ["[0:v]ass=subs.ass:fontsdir=.[v]"]
    music_files = list(Path(tmp).glob("music.*"))
    if has_music and music_files:
        inputs += ["-i", music_files[0].name]
        fade_start = max(0.0, total - 1.5)
        filters.append(f"[1:a]apad[va];[2:a]volume={MUSIC_VOLUME},afade=t=out:st={fade_start:.2f}:d=1.5[m];"
                       "[va][m]amix=inputs=2:duration=first:normalize=0[a]")
    else:
        filters.append("[1:a]apad[a]")

    cmd = [ffmpeg, "-y", *inputs, "-filter_complex", ";".join(filters),
           "-map", "[v]", "-map", "[a]", "-t", f"{total + 0.3:.2f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out_path)]
    run(cmd, cwd=tmp)


# ---------------------------------------------------------------- post kit


def post_kit_text(pkg, item, hook_index, music_credit=None, has_thumb=False, stock_authors=None):
    lines = [
        f"POST KIT - {pkg.get('title', 'untitled')}",
        f"Platform: {pkg.get('platform', '?')} | Runtime setting: {pkg.get('runtimeLabel', '?')} | Voice: {pkg.get('voice', '?')}",
        f"Hook used in video: #{hook_index + 1}",
        "",
        "CAPTION OPTIONS (paste one):",
    ]
    for i, cap in enumerate(pkg.get("captions", []), 1):
        lines += [f"{i}. {cap}", ""]
    lines.append("TITLE / THUMBNAIL TEXT IDEAS:")
    lines += [f'- "{t}"' for t in pkg.get("thumbnails", [])]
    lines.append("")
    if has_thumb:
        lines += [
            "COVER IMAGE: a matching -thumb.jpg was saved next to this video.",
            "Upload it as the cover/thumbnail so the platform doesn't pick a random frame.",
            "",
        ]
    if music_credit:
        lines += [
            "MUSIC CREDIT (required - paste into the video description):",
            music_credit,
            "",
        ]
    if stock_authors:
        who = ", ".join(sorted(stock_authors))
        lines += [
            "STOCK VIDEO: clips via Pexels (pexels.com) - attribution appreciated.",
            f"Videographers: {who}." if who else "",
            "",
        ]
    if item.get("notes"):
        lines += [f"YOUR QUEUE NOTES: {item['notes']}", ""]
    lines += [
        "BEFORE POSTING:",
        "- Watch the whole video once. You are the editor of record.",
        "- Enable the platform's AI-generated content disclosure (AI voice).",
        f"- Safety framing for this scenario: {pkg.get('safety', '')}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- main


def load_items(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "items" in data:
        return [(it.get("slot", i + 1), it, it["package"]) for i, it in enumerate(data["items"])]
    if isinstance(data, dict) and "hooks" in data:
        return [(1, {}, data)]
    sys.exit("Unrecognized JSON - export it from the app (Export queue / Export .json).")


def main():
    parser = argparse.ArgumentParser(description="Render What If Studio queue exports into finished vertical videos.")
    parser.add_argument("queue", nargs="?", default="whatifstudio-queue.json",
                        help="Queue or package .json exported from the app")
    parser.add_argument("--out", default="output", help="Output folder (default: output)")
    parser.add_argument("--backgrounds", default="backgrounds",
                        help="Folder of visuals; several files = one clip per beat, in order")
    parser.add_argument("--music", default="music", help="Folder of background music (optional)")
    parser.add_argument("--ai-visuals", action="store_true",
                        help="Generate one free AI image per beat (Pollinations, no account) instead of using backgrounds/")
    parser.add_argument("--ai-style", default="cinematic", choices=sorted(AI_STYLES),
                        help="Look of generated AI visuals (default: cinematic)")
    parser.add_argument("--ai-cache", default="ai-visuals",
                        help="Cache folder for generated images (default: ai-visuals)")
    parser.add_argument("--charts", action="store_true",
                        help="Overlay an animated counter/bar on beats with a headline number (needs per-beat visuals)")
    parser.add_argument("--stock", action="store_true",
                        help="Use real Pexels stock video per beat (needs a free PEXELS_API_KEY / pipeline/pexels_key.txt)")
    parser.add_argument("--stock-cache", default="stock",
                        help="Cache folder for downloaded stock clips (default: stock)")
    parser.add_argument("--infer", action="store_true",
                        help="Generate a paid AI-video clip per beat via tryinfer (needs TRYINFER_API_KEY / pipeline/tryinfer_key.txt)")
    parser.add_argument("--infer-model", default="seedance-2.0-pro",
                        help="tryinfer model id (default: seedance-2.0-pro)")
    parser.add_argument("--infer-task", default="image-to-video",
                        choices=["image-to-video", "text-to-video"],
                        help="tryinfer task; image-to-video animates a free Pollinations first frame (default)")
    parser.add_argument("--infer-duration", default="5", choices=["5", "10"],
                        help="Seconds per generated clip (default: 5; clips loop to fill each beat)")
    parser.add_argument("--infer-cache", default="infer-videos",
                        help="Cache folder for generated AI clips (default: infer-videos)")
    parser.add_argument("--elevenlabs", action="store_true",
                        help="Use ElevenLabs for the voiceover (needs ELEVENLABS_API_KEY / pipeline/elevenlabs_key.txt)")
    parser.add_argument("--el-voice", help="ElevenLabs voice name or id (default: mapped from the package's voice style)")
    parser.add_argument("--el-model", default="eleven_multilingual_v2",
                        help="ElevenLabs model id (default: eleven_multilingual_v2)")
    parser.add_argument("--hook", type=int, default=1, choices=[1, 2, 3],
                        help="Which of the 3 hooks opens the video (default: 1)")
    parser.add_argument("--voice", help="Override edge-tts voice for all items")
    parser.add_argument("--rate", help="Override speech rate, e.g. +10%%")
    parser.add_argument("--pitch", help="Override speech pitch, e.g. -2Hz")
    parser.add_argument("--slots", help="Only render these queue slots, e.g. 1,3,4")
    args = parser.parse_args()

    if not CAPTION_FONT_FILE.exists():
        print(f"Note: caption font missing at {CAPTION_FONT_FILE}; captions may fall back to a default font.")

    ffmpeg = find_tool("ffmpeg")
    ffprobe = find_tool("ffprobe")

    items = load_items(args.queue)
    if args.slots:
        wanted = {int(s) for s in args.slots.split(",")}
        items = [it for it in items if it[0] in wanted]
    if not items:
        sys.exit("Nothing to render - the queue export has no packages (or --slots matched none).")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    hook_index = args.hook - 1
    visuals = list_visuals(args.backgrounds)

    stock_key = None
    if args.stock:
        stock_key = pexels_api_key()
        if not stock_key:
            sys.exit(
                "--stock needs a free Pexels API key.\n"
                "  1. Sign up (free) at https://www.pexels.com/api/ and copy your key.\n"
                "  2. Either set the PEXELS_API_KEY environment variable, or save the key in\n"
                "     pipeline/pexels_key.txt (one line). Then re-run.")

    infer_key = None
    if args.infer:
        infer_key = infer_api_key()
        if not infer_key:
            sys.exit(
                "--infer needs your tryinfer API key.\n"
                "  Set the TRYINFER_API_KEY environment variable, or save the key (one line)\n"
                "  in pipeline/tryinfer_key.txt. Then re-run.")
        print("NOTE: --infer uses the PAID tryinfer API - one clip is billed per beat.\n")

    el_key = None
    if args.elevenlabs:
        el_key = elevenlabs_key()
        if not el_key:
            sys.exit(
                "--elevenlabs needs your ElevenLabs API key.\n"
                "  Grab it from elevenlabs.io (profile icon -> API keys), then either set the\n"
                "  ELEVENLABS_API_KEY environment variable or save it (one line) in\n"
                "  pipeline/elevenlabs_key.txt. Then re-run.")

    print(f"Rendering {len(items)} video(s) -> {out_dir.resolve()}")
    if args.infer:
        print(f"Visuals: tryinfer AI video per beat (model: {args.infer_model}, {args.infer_duration}s clips)")
    elif args.stock:
        print(f"Visuals: Pexels stock video per beat (cache: {args.stock_cache})")
    elif args.ai_visuals:
        print(f"Visuals: free AI images per beat (style: {args.ai_style}, cache: {args.ai_cache})")
    else:
        print(f"Visuals: {len(visuals)} file(s) in '{args.backgrounds}'"
              + (" (one clip per beat)" if len(visuals) > 1 else " (single background)" if visuals else " (animated gradient)"))
    print()
    failures = 0

    for slot, item, pkg in items:
        title = pkg.get("title", "untitled")
        slug = f"{slot:02d}-{slugify(title)}"
        out_path = out_dir / f"{slug}.mp4"
        print(f"[slot {slot}] {title}")

        vconf = dict(VOICE_MAP.get(pkg.get("voice"), DEFAULT_VOICE))
        if args.voice:
            vconf["voice"] = args.voice
        if args.rate:
            vconf["rate"] = args.rate
        if args.pitch:
            vconf["pitch"] = args.pitch

        segments = narration_segments(pkg, hook_index)
        text = " ".join(segments)
        if not text:
            print("  SKIP: package has no narration text\n")
            failures += 1
            continue

        try:
            with tempfile.TemporaryDirectory() as tmpname:
                tmp = Path(tmpname)
                if CAPTION_FONT_FILE.exists():
                    shutil.copy(CAPTION_FONT_FILE, tmp / CAPTION_FONT_FILE.name)

                if args.elevenlabs:
                    el_voice_id, el_voice_name = pick_elevenlabs_voice(
                        pkg.get("voice", ""), args.el_voice, el_key)
                    words = synthesize_elevenlabs(text, el_voice_id, args.el_model, tmp / "voice.mp3", el_key)
                    total = probe_duration(ffprobe, tmp / "voice.mp3")
                    print(f"  voice: ElevenLabs {el_voice_name} ({args.el_model}) - {total:.1f}s")
                else:
                    words = asyncio.run(synthesize(text, vconf, tmp / "voice.mp3"))
                    total = probe_duration(ffprobe, tmp / "voice.mp3")
                    print(f"  voice: {vconf['voice']} ({vconf['rate']}, {vconf['pitch']}) - {total:.1f}s")
                (tmp / "subs.ass").write_text(words_to_ass(words, pkg, total), encoding="utf-8")

                item_visuals = visuals
                stock_authors = set()
                if args.infer:
                    print(f"  generating AI video with {args.infer_model}...")
                    item_visuals = generate_infer_videos(pkg, segments, infer_key, args.infer_model,
                                                         args.infer_task, args.infer_duration, args.infer_cache)
                elif args.stock:
                    print("  fetching Pexels stock footage...")
                    item_visuals = fetch_stock_visuals(pkg, segments, stock_key, args.stock_cache, stock_authors)
                elif args.ai_visuals:
                    print(f"  generating AI visuals ({args.ai_style})...")
                    item_visuals = generate_ai_visuals(pkg, len(segments), args.ai_style, args.ai_cache)

                charts = None
                if args.charts:
                    # Charts only on body beats (skip hook/segment 0 and the outro,
                    # which the title card and CTA card own).
                    charts = [None] * len(segments)
                    hits = 0
                    for i in range(1, len(segments) - 1):
                        spec = detect_chart(segments[i])
                        charts[i] = spec
                        if spec:
                            hits += 1
                    print(f"  charts: {hits} beat(s) with an animated number")
                # Bare filename works because segment clips render with cwd=tmp,
                # where the font was copied; an absolute Windows path's drive
                # colon breaks the ffmpeg filtergraph parser.
                font_ff = CAPTION_FONT_FILE.name if CAPTION_FONT_FILE.exists() else None

                base = None
                if len(item_visuals) > 1:
                    spans = segment_spans(segments, words, total)
                    base = build_clip_base(ffmpeg, item_visuals, spans, tmp, charts=charts, font_ff=font_ff)
                    print(f"  visuals: {len(spans)} beat clips from {len(item_visuals)} source file(s)")
                elif len(item_visuals) == 1:
                    seg = tmp / "base.mp4"
                    render_segment_clip(ffmpeg, item_visuals[0], total + 0.4, seg)
                    base = seg
                    print(f"  visuals: single background ({item_visuals[0].name})")
                else:
                    print("  visuals: generated gradient")

                music = pick_music(pkg, args.music)
                if music:
                    shutil.copy(music, tmp / ("music" + music.suffix))
                    print(f"  music: {music.parent.name}/{music.name}")

                final_render(ffmpeg, base, pkg, total, bool(music), out_path.resolve(), tmp)

                thumb_made = False
                if font_ff:
                    first_visual = item_visuals[0] if item_visuals else None
                    try:
                        render_thumbnail(ffmpeg, first_visual, pkg,
                                         (out_dir / f"{slug}-thumb.jpg").resolve(), tmp, font_ff)
                        thumb_made = True
                    except Exception as exc:
                        print(f"  (thumbnail skipped: {exc})")

            credit = music_credit_for(music, args.music)
            (out_dir / f"{slug}-post.txt").write_text(
                post_kit_text(pkg, item, hook_index, credit, thumb_made, stock_authors), encoding="utf-8")
            extras = f"{slug}-post.txt" + (f" + {slug}-thumb.jpg" if thumb_made else "")
            print(f"  done: {out_path.name} + {extras}\n")
        except Exception as exc:
            failures += 1
            print(f"  FAILED: {exc}\n")

    rendered = len(items) - failures
    print(f"Finished: {rendered}/{len(items)} rendered.")
    if rendered:
        print("Review each video, then post it yourself with the matching -post.txt caption.")
        print("Remember to enable the AI-generated content disclosure on TikTok/YouTube.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
