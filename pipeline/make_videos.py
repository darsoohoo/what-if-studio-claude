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


def render_segment_clip(ffmpeg, visual, duration, out_path, index=0):
    """Scale/crop one visual to a full-frame vertical clip of the given length.
    Still images get an alternating camera move (in / pan / out / pan back)."""
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
    run([ffmpeg, "-y", *loop, "-i", str(visual), "-t", f"{duration:.2f}", "-vf", vf, "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out_path)])


def build_clip_base(ffmpeg, visuals, spans, tmp):
    """One clip per beat with alternating motion, joined by crossfades.
    Segments before the last are rendered XFADE_DUR longer so the fades
    consume the extra tail and the visual timeline stays in sync with audio."""
    durs = [round(max(0.4, end - start), 2) for start, end in spans]
    seg_files = []
    for i, dur in enumerate(durs):
        seg = tmp / f"seg_{i:02d}.mp4"
        extra = XFADE_DUR if i < len(durs) - 1 else 0.5
        render_segment_clip(ffmpeg, visuals[i % len(visuals)], dur + extra, seg, index=i)
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
        filters.append("[1:a]apad[va];[2:a]volume=0.12[m];[va][m]amix=inputs=2:duration=first:normalize=0[a]")
    else:
        filters.append("[1:a]apad[a]")

    cmd = [ffmpeg, "-y", *inputs, "-filter_complex", ";".join(filters),
           "-map", "[v]", "-map", "[a]", "-t", f"{total + 0.3:.2f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out_path)]
    run(cmd, cwd=tmp)


# ---------------------------------------------------------------- post kit


def post_kit_text(pkg, item, hook_index):
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

    print(f"Rendering {len(items)} video(s) -> {out_dir.resolve()}")
    if args.ai_visuals:
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

                words = asyncio.run(synthesize(text, vconf, tmp / "voice.mp3"))
                total = probe_duration(ffprobe, tmp / "voice.mp3")
                (tmp / "subs.ass").write_text(words_to_ass(words, pkg, total), encoding="utf-8")
                print(f"  voice: {vconf['voice']} ({vconf['rate']}, {vconf['pitch']}) - {total:.1f}s")

                item_visuals = visuals
                if args.ai_visuals:
                    print(f"  generating AI visuals ({args.ai_style})...")
                    item_visuals = generate_ai_visuals(pkg, len(segments), args.ai_style, args.ai_cache)

                base = None
                if len(item_visuals) > 1:
                    spans = segment_spans(segments, words, total)
                    base = build_clip_base(ffmpeg, item_visuals, spans, tmp)
                    print(f"  visuals: {len(spans)} beat clips from {len(item_visuals)} source file(s)")
                elif len(item_visuals) == 1:
                    seg = tmp / "base.mp4"
                    render_segment_clip(ffmpeg, item_visuals[0], total + 0.4, seg)
                    base = seg
                    print(f"  visuals: single background ({item_visuals[0].name})")
                else:
                    print("  visuals: generated gradient")

                music = pick_file(args.music, AUDIO_EXTS)
                if music:
                    shutil.copy(music, tmp / ("music" + music.suffix))
                    print(f"  music: {music.name}")

                final_render(ffmpeg, base, pkg, total, bool(music), out_path.resolve(), tmp)

            (out_dir / f"{slug}-post.txt").write_text(post_kit_text(pkg, item, hook_index), encoding="utf-8")
            print(f"  done: {out_path.name} + {slug}-post.txt\n")
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
