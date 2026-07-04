#!/usr/bin/env python3
"""
What If Studio - companion video pipeline.

Turns a queue export from the app (whatifstudio-queue.json) into finished
vertical videos: AI voiceover (Microsoft neural voices via edge-tts) +
background visuals + word-synced burned-in captions, rendered with ffmpeg.

This tool is OPTIONAL and lives alongside the static app. The app itself
never requires it. Nothing here posts anywhere - you review and upload
your own videos.

Usage:
    python make_videos.py whatifstudio-queue.json
    python make_videos.py package.json --hook 2
    python make_videos.py queue.json --backgrounds backgrounds --music music

Requirements: Python 3.9+, `pip install -r requirements.txt`, ffmpeg on PATH
(or installed via winget - it is auto-detected). edge-tts needs internet.
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

# App voice style -> edge-tts voice + delivery tweaks
VOICE_MAP = {
    "Calm Narrator":            {"voice": "en-US-ChristopherNeural", "rate": "-5%",  "pitch": "-2Hz"},
    "High-Energy Storyteller":  {"voice": "en-US-GuyNeural",         "rate": "+12%", "pitch": "+2Hz"},
    "Deadpan Documentarian":    {"voice": "en-US-EricNeural",        "rate": "-8%",  "pitch": "-4Hz"},
}
DEFAULT_VOICE = {"voice": "en-US-ChristopherNeural", "rate": "+0%", "pitch": "+0Hz"}

SUB_STYLE = (
    "Fontname=Arial,FontSize=15,Bold=1,"
    "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
    "Outline=2,Shadow=0,Alignment=10,MarginL=40,MarginR=40"
)

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


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "package"


def clean_for_tts(text):
    """Strip emoji/symbols the voice would mangle; keep normal punctuation."""
    text = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def narration_text(pkg, hook_index):
    hooks = pkg.get("hooks", [])
    hook = hooks[min(hook_index, len(hooks) - 1)] if hooks else ""
    parts = [hook] + list(pkg.get("beats", [])) + [pkg.get("outro", "")]
    return " ".join(clean_for_tts(p) for p in parts if p and p.strip())


def hex_to_ffmpeg(color, fallback):
    if isinstance(color, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        return "0x" + color[1:]
    return fallback


def srt_time(seconds):
    ms = max(0, int(round(seconds * 1000)))
    return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d},{ms % 1000:03d}"


# ---------------------------------------------------------------- TTS + subs


async def synthesize(text, vconf, mp3_path):
    """Generate speech and collect word-boundary timings (100ns ticks)."""
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


def words_to_srt(words, max_words=4, max_gap=0.6, tail_pad=0.15):
    """Group word timings into short phrase cues (TikTok-style captions)."""
    cues = []
    current = []
    for i, (start, end, word) in enumerate(words):
        if current:
            prev_end = current[-1][1]
            sentence_break = current[-1][2].rstrip('"”’').endswith((".", "!", "?", ":"))
            if len(current) >= max_words or (start - prev_end) > max_gap or sentence_break:
                cues.append(current)
                current = []
        current.append((start, end, word))
    if current:
        cues.append(current)

    lines = []
    for i, cue in enumerate(cues):
        start = cue[0][0]
        end = cue[-1][1] + tail_pad
        if i + 1 < len(cues):
            end = min(end, cues[i + 1][0][0] - 0.01)
        text = " ".join(w for _, _, w in cue)
        lines.append(f"{i + 1}\n{srt_time(start)} --> {srt_time(end)}\n{text}\n")
    return "\n".join(lines)


# ---------------------------------------------------------------- rendering


def probe_duration(ffprobe, media_path):
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(media_path)],
        capture_output=True, text=True, check=True
    )
    return float(out.stdout.strip())


def pick_file(directory, exts):
    if not directory:
        return None
    folder = Path(directory)
    if not folder.is_dir():
        return None
    files = [f for f in folder.iterdir() if f.suffix.lower() in exts]
    return random.choice(files) if files else None


def build_ffmpeg_command(ffmpeg, pkg, mp3_path, srt_name, out_path, duration, background, music):
    total = duration + 0.4

    if background and background.suffix.lower() in IMAGE_EXTS:
        bg_args = ["-loop", "1", "-i", str(background)]
    elif background:
        bg_args = ["-stream_loop", "-1", "-i", str(background)]
    else:
        colors = pkg.get("colors") or {}
        c0 = hex_to_ffmpeg(colors.get("from"), "0x151a30")
        c1 = hex_to_ffmpeg(colors.get("to"), "0x6a5ae0")
        bg_args = ["-f", "lavfi", "-i",
                   f"gradients=s={WIDTH}x{HEIGHT}:c0={c0}:c1={c1}:speed=0.015:rate={FPS}"]

    cmd = [ffmpeg, "-y", *bg_args, "-i", str(mp3_path)]
    filters = [
        f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS},"
        f"subtitles={srt_name}:force_style='{SUB_STYLE}'[v]"
    ]

    if music:
        cmd += ["-i", str(music)]
        filters.append("[1:a]apad[va];[2:a]volume=0.12[m];[va][m]amix=inputs=2:duration=first:normalize=0[a]")
        audio_map = "[a]"
    else:
        filters.append("[1:a]apad[a]")
        audio_map = "[a]"

    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", "[v]", "-map", audio_map,
        "-t", f"{total:.2f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(out_path),
    ]
    return cmd


def post_kit_text(pkg, item, hook_index):
    lines = []
    lines.append(f"POST KIT - {pkg.get('title', 'untitled')}")
    lines.append(f"Platform: {pkg.get('platform', '?')} | Runtime setting: {pkg.get('runtimeLabel', '?')} | Voice: {pkg.get('voice', '?')}")
    lines.append(f"Hook used in video: #{hook_index + 1}")
    lines.append("")
    lines.append("CAPTION OPTIONS (paste one):")
    for i, cap in enumerate(pkg.get("captions", []), 1):
        lines.append(f"{i}. {cap}")
        lines.append("")
    lines.append("TITLE / THUMBNAIL TEXT IDEAS:")
    for t in pkg.get("thumbnails", []):
        lines.append(f'- "{t}"')
    lines.append("")
    if item.get("notes"):
        lines.append(f"YOUR QUEUE NOTES: {item['notes']}")
        lines.append("")
    lines.append("BEFORE POSTING:")
    lines.append("- Watch the whole video once. You are the editor of record.")
    lines.append("- Enable the platform's AI-generated content disclosure (AI voice).")
    lines.append(f"- Safety framing for this scenario: {pkg.get('safety', '')}")
    return "\n".join(lines)


# ---------------------------------------------------------------- main


def load_items(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "items" in data:          # queue export
        return [(item.get("slot", i + 1), item, item["package"]) for i, item in enumerate(data["items"])]
    if isinstance(data, dict) and "hooks" in data:          # single package export
        return [(1, {}, data)]
    sys.exit("Unrecognized JSON - export it from the app (Export queue / Export .json).")


def main():
    parser = argparse.ArgumentParser(description="Render What If Studio queue exports into finished vertical videos.")
    parser.add_argument("queue", nargs="?", default="whatifstudio-queue.json",
                        help="Queue or package .json exported from the app")
    parser.add_argument("--out", default="output", help="Output folder (default: output)")
    parser.add_argument("--backgrounds", default="backgrounds",
                        help="Folder of background videos/images; if empty, animated gradients are generated")
    parser.add_argument("--music", default="music",
                        help="Folder of background music; if empty, no music is mixed")
    parser.add_argument("--hook", type=int, default=1, choices=[1, 2, 3],
                        help="Which of the 3 hooks opens the video (default: 1)")
    parser.add_argument("--voice", help="Override edge-tts voice for all items (e.g. en-US-AriaNeural)")
    parser.add_argument("--rate", help="Override speech rate, e.g. +10%%")
    parser.add_argument("--pitch", help="Override speech pitch, e.g. -2Hz")
    parser.add_argument("--slots", help="Only render these queue slots, e.g. 1,3,4")
    args = parser.parse_args()

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

    print(f"Rendering {len(items)} video(s) -> {out_dir.resolve()}\n")
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

        text = narration_text(pkg, hook_index)
        if not text:
            print("  SKIP: package has no narration text\n")
            failures += 1
            continue

        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                mp3_path = tmp / "voice.mp3"
                words = asyncio.run(synthesize(text, vconf, mp3_path))
                (tmp / "subs.srt").write_text(words_to_srt(words), encoding="utf-8")
                duration = probe_duration(ffprobe, mp3_path)
                print(f"  voice: {vconf['voice']} ({vconf['rate']}, {vconf['pitch']}) - {duration:.1f}s")

                background = pick_file(args.backgrounds, VIDEO_EXTS | IMAGE_EXTS)
                music = pick_file(args.music, AUDIO_EXTS)
                print(f"  background: {background.name if background else 'generated gradient'}"
                      + (f" | music: {music.name}" if music else ""))

                cmd = build_ffmpeg_command(ffmpeg, pkg, mp3_path, "subs.srt", out_path.resolve(),
                                           duration, background, music)
                result = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError("ffmpeg failed:\n" + result.stderr[-1500:])

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
