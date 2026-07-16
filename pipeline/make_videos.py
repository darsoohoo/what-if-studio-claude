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
import array
import asyncio
import base64
import glob
import json
import math
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
import wave
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
    "Scary Story": "eerie",
    "True History": "period",
    "AI Remake": "trailer",
}
MUSIC_VOLUME = 0.12

# Free AI image generation (Pollinations - no account, no key).
# Each style is a prompt suffix appended to the scenario's shot description.
AI_STYLES = {
    "cinematic":   "vertical cinematic digital art, dramatic lighting, rich colors, high detail, no text, no words, no letters",
    "3d":          "soft 3d pixar style render, cinematic lighting, expressive characters, high detail, no text, no words, no letters",
    "infographic": "flat design vector illustration, corporate infographic style, soft pastel beige background, simple geometric shapes and characters, clean minimal composition, no text, no words, no letters",
    "dark":        "moody dark atmospheric illustration, deep shadows, single strong light source, eerie but tasteful, high detail, no text, no words, no letters",
    "archival":    "aged archival photograph blended with classical oil painting, sepia and muted earth tones, dramatic historical scene, subtle film grain, high detail, no text, no words, no letters",
    "eerie":       "cinematic horror film still, muted desaturated colors, symmetrical composition, unnervingly still, ordinary place with something subtly wrong, natural window light or sodium streetlight, 35mm film grain, quiet dread, high detail, no text, no words, no letters",
}
AI_IMAGE_HOST = "https://image.pollinations.ai/prompt/"

# 🎭 Mood looks: appended to the style suffix of every generated visual
# (free Pollinations images, paid tryinfer images, and AI-video first
# frames/motion) when --mood is passed. Keys mirror MOODS in review.py.
# No mood flag = exactly the classic look; caches are NOT forked by mood,
# so re-renders stay free (delete a scenario's cache entry to restyle it).
MOOD_LOOKS = {
    "eerie": "unsettling atmosphere, muted desaturated palette, quiet dread in the stillness",
    "funny": "bright playful atmosphere, warm saturated colors, comic timing in the poses",
    "sarcastic": "glossy advertising perfection with one detail played visibly straight-faced wrong",
    "witty": "clever visual gag staged in frame, crisp clean lighting",
    "adventurous": "epic wide adventure feel, golden-hour light, dynamic diagonal motion",
    "dramatic": "high-contrast dramatic lighting, deep shadows, tense staging",
    "mysterious": "fog and half-light, subjects partly hidden, cool blue-grey tones",
    "wholesome": "soft warm cozy light, gentle expressions, pastel tones",
    "inspiring": "sunrise glow, hopeful upward framing, expansive sky",
    "deadpan": "flat symmetrical composition, even lighting, expressionless subjects held perfectly still",
    "trailer": "epic movie-trailer frame, anamorphic cinematic look, teal and orange grade, dramatic rim light, atmospheric haze, larger-than-life scale",
    "trailer-vo": "epic movie-trailer frame, anamorphic cinematic look, teal and orange grade, dramatic rim light, atmospheric haze, larger-than-life scale",
}


def styled_suffix(style_suffix, mood):
    """The style tail for generated visuals, with the mood look folded in."""
    look = MOOD_LOOKS.get(mood or "")
    return f"{style_suffix}, {look}" if look else style_suffix

# Category branding: story categories get their own burned-in follow card,
# anchor hashtag, default AI-visual style, and title-card/cover typography.
# Anything not listed renders with the classic what-if brand. Keys mirror
# CATEGORIES in app.js. font = a .ttf in pipeline/assets; font_name = the
# family name INSIDE that ttf (libass matches by family, not filename).
# title_color is ASS &HAABBGGRR&; thumb_color is ffmpeg 0xRRGGBB.
DEFAULT_BRANDING = {
    "cta": "FOLLOW FOR THE NEXT WHAT-IF", "anchor": "#whatif", "style": "cinematic",
    "font": None, "font_name": CAPTION_FONT_NAME,
    "title_color": r"&H0000D4FF&", "thumb_color": "0xF5C400",       # signature yellow
    # Typography tuning (defaults = the classic look). Thin display faces
    # want wide tracking and a much lighter outline than bold ones.
    "title_spacing": 1, "title_outline": 9, "title_shadow": 3,
    "cta_outline": 6, "thumb_border": 9,
    "music_volume": MUSIC_VOLUME,
    # Beat-timed sound design: "reveal" = a sub-bass riser that swells into
    # the reveal beat and lands with a soft impact (synthesized, no samples).
    "sfx": None,
}
CATEGORY_BRANDING = {
    "Scary Story": {
        # Art-house horror poster look: thin caps, wide tracking, bone white.
        "cta": "FOLLOW FOR MORE SCARY STORIES", "anchor": "#scarystories", "style": "eerie",
        "font": "JuliusSansOne-Regular.ttf", "font_name": "Julius Sans One",
        "title_color": r"&H00E0E8ED&", "thumb_color": "0xEDE8E0",   # bone white
        "title_spacing": 7, "title_outline": 3, "title_shadow": 2,
        "cta_outline": 3, "thumb_border": 5,
        # Horror leans on the bed: the creepy track sits a notch louder,
        # and the reveal beat gets a riser + soft impact under it.
        "music_volume": 0.16,
        "sfx": "reveal",
    },
    "True History": {
        "cta": "FOLLOW FOR MORE TRUE HISTORY", "anchor": "#history", "style": "archival",
        "font": "IMFellEnglishSC-Regular.ttf", "font_name": "IM FELL English SC",
        "title_color": r"&H007AC9E8&", "thumb_color": "0xE8C97A",   # parchment gold
    },
    # "If <movie> was AI-generated": trailer-first format - epic bed by
    # default (MOOD_BY_CATEGORY sends it to music/trailer), electric violet
    # title, reveal sound design like the story categories.
    "AI Remake": {
        "cta": "FOLLOW FOR MORE AI REMAKES", "anchor": "#aitrailer", "style": "cinematic",
        "title_color": r"&H00F72F7B&", "thumb_color": "0xB05CFF",   # electric violet
        "music_volume": 0.16,
        "sfx": "reveal",
    },
}


def branding_for(pkg):
    """The full branding (CTA/anchor/style/typography) for a package's category."""
    brand = dict(DEFAULT_BRANDING)
    brand.update(CATEGORY_BRANDING.get((pkg or {}).get("category", ""), {}))
    return brand


def brand_font(pkg):
    """(path, family) of the category's display font; falls back to the
    caption font when the category has none or its .ttf is missing."""
    brand = branding_for(pkg)
    if brand["font"]:
        path = ASSETS / brand["font"]
        if path.exists():
            return path, brand["font_name"]
    return None, CAPTION_FONT_NAME

# Modern caption look (ASS): white words, spoken word pops to yellow.
CAP_WHITE = r"&H00FFFFFF&"
CAP_HL = r"&H0000D4FF&"      # bright yellow (ASS is &HAABBGGRR)
# Dialogue caption tints, one per character by order of appearance (BGR):
# ice blue, rose, mint - the spoken-word pop stays yellow for everyone.
CAP_SPEAKER_TINTS = [r"&H00F0DCA8&", r"&H00CCB4F0&", r"&H00C8EFB8&"]
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


def versioned_slug(out_dir, slug):
    """Never overwrite an existing render: when slug.mp4 is already there,
    bump to -v2, -v3, ... so every render of a package is kept side by side
    (the post kit and thumbnail share the slug, so they version together)."""
    if not (Path(out_dir) / f"{slug}.mp4").exists():
        return slug
    v = 2
    while (Path(out_dir) / f"{slug}-v{v}.mp4").exists():
        v += 1
    return f"{slug}-v{v}"


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


# Score genres for --trailer: which tracks fit which kind of story. The
# writer picks the genre (pkg["score"]), infer_score guesses from the story
# when it didn't, --score forces one. Track stems are searched across every
# music/ folder, so genres can borrow from mood folders (wonder does).
TRAILER_SCORES = {
    "action":  ["Five Armies", "Prelude and Action", "Volatile Reaction"],
    "dark":    ["Stormfront", "Achilles", "Lightless Dawn"],
    "tragedy": ["Heartbreaking", "Sad Trio", "Long Note Three"],
    "wonder":  ["Frozen Star", "Floating Cities"],
}

_SCORE_HINTS = {
    "tragedy": "love loss lost goodbye sink sinking sank drown drowning ocean liner "
               "dies died death dying farewell heart tears widow funeral doomed "
               "tragedy grief mourning titanic",
    "action":  "war battle chase heist fight fighting soldier gun race escape "
               "explosion mission agent revenge army invasion uprising rebellion "
               "warrior sword arena",
    "wonder":  "space stars galaxy magic wonder discover discovery dream fantasy "
               "kingdom dinosaur miracle wish evolve evolved future civilization "
               "planet universe",
    "dark":    "haunted ghost demon monster curse cursed whisper shadow vanish "
               "vanished missing basement ritual possessed evil scream horror "
               "nightmare stalks lurks",
}


def infer_score(pkg):
    """Guess the trailer score genre from the story when the writer didn't
    set one - keyword hits on title + premise + tags, horror bias last."""
    text = " ".join([pkg.get("title", ""), pkg.get("premise", ""),
                     " ".join(pkg.get("tags") or [])]).lower()
    words = set(re.findall(r"[a-z']+", text))
    best, hits = None, 0
    for genre, hint in _SCORE_HINTS.items():
        n = len(words & set(hint.split()))
        if n > hits:
            best, hits = genre, n
    if best:
        return best
    return "dark" if branding_for(pkg).get("sfx") == "reveal" else "action"


def pick_music(pkg, music_dir, override=None, score=None):
    """Pick a track matching the scenario's mood; fall back to loose files.
    `override` replaces the category mood: "ironic" = a sincerely cheerful
    bed (upbeat fills in if the folder is empty), "trailer" = an epic
    cinematic bed (tense fills in). Both folders come from get_music.py.
    `score` (trailer only) narrows to that genre's tracks from
    TRAILER_SCORES wherever they live under music/."""
    root = Path(music_dir) if music_dir else None
    if not root or not root.is_dir():
        return None
    fallback = {"ironic": "upbeat", "trailer": "tense"}
    if override in fallback:
        if override == "trailer" and score:
            stems = {s.lower() for s in TRAILER_SCORES.get(score, ())}
            pool = [f for f in root.rglob("*")
                    if f.suffix.lower() in AUDIO_EXTS and f.stem.lower() in stems]
            if pool:
                return random.choice(pool)
        return (pick_file(root / override, AUDIO_EXTS)
                or pick_file(root / fallback[override], AUDIO_EXTS)
                or pick_file(root, AUDIO_EXTS))
    mood = MOOD_BY_CATEGORY.get(pkg.get("category", ""), "wonder")
    return pick_file(root / mood, AUDIO_EXTS) or pick_file(root, AUDIO_EXTS)


def ironic_music_treatment(ffmpeg, src, dest, reveal, mode="tail"):
    """Rebuild a cheerful bed so it dies on the reveal (the Jordan Peele
    trick: the song stays SINCERELY happy, the picture goes wrong). Up to
    `reveal` the track plays straight, a notch louder than a normal bed;
    then a ~0.45s tape-stop (three slurring pitch-drop chunks), a beat of
    silence, and either nothing more ("stop") or the song resuming slowed
    ~7% and quieter ("tail" - like it's playing from another room).
    Levels are relative: final_render still applies the branding volume
    and end fade on top."""
    r = float(reveal)
    st = "aformat=sample_fmts=fltp:channel_layouts=stereo"
    segs = [
        f"[0:a]aresample=44100,{st},asplit=5[p][s1][s2][s3][t]",
        f"[p]atrim=0:{r:.3f},asetpts=PTS-STARTPTS,volume=1.25[pre]",
    ]
    labels = ["[pre]"]
    for j, (rate, vol) in enumerate(((0.84, 1.0), (0.62, 0.7), (0.42, 0.4)), 1):
        a, b = r + 0.15 * (j - 1), r + 0.15 * j
        segs.append(f"[s{j}]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,"
                    f"asetrate={int(44100 * rate)},aresample=44100,{st},"
                    f"volume={vol}[c{j}]")
        labels.append(f"[c{j}]")
    segs.append(f"anullsrc=r=44100:cl=stereo,atrim=0:0.6,{st}[gap]")
    labels.append("[gap]")
    if mode == "tail":
        segs.append(f"[t]atrim={r + 0.45:.3f},asetpts=PTS-STARTPTS,"
                    f"asetrate={int(44100 * 0.93)},aresample=44100,{st},"
                    f"volume=0.45,afade=t=in:st=0:d=1.2[tl]")
        labels.append("[tl]")
    else:
        segs.append("[t]atrim=0:0.05,asetpts=PTS-STARTPTS,volume=0[tl]")
        labels.append("[tl]")
    segs.append("".join(labels) + f"concat=n={len(labels)}:v=0:a=1[out]")
    run([ffmpeg, "-y", "-i", str(src), "-filter_complex", ";".join(segs),
         "-map", "[out]", "-c:a", "pcm_s16le", str(dest)])


def music_credit_for(music, music_dir):
    """Look up the license credit line for a track (written by get_music.py)."""
    if not music:
        return None
    try:
        credits = json.loads((Path(music_dir) / "credits.json").read_text(encoding="utf-8"))
        return credits.get(music.name)
    except Exception:
        return None


def is_ref_file(f):
    """Per-beat reference images/videos (ref-NN.jpg, refv-NN.mp4) live beside
    the staged clips but are targeted inputs, not ordered visuals."""
    return f.name.startswith(("ref-", "refv-"))


def list_visuals(directory):
    folder = Path(directory) if directory else None
    if not folder or not folder.is_dir():
        return []
    return sorted(f for f in folder.iterdir()
                  if f.suffix.lower() in (VIDEO_EXTS | IMAGE_EXTS) and not is_ref_file(f))


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


# --------------------------------------------- trailer dialogue (multi-voice)
# A narration line may embed in-scene character lines in the form
#   [Name] "the line"
# (the Trailer mood writes these). Each named character speaks with their own
# cast voice plus a light in-scene room tone; the narrator keeps the normal
# voice. The tag itself is never spoken or captioned - the quoted words are.

_DLG_RE = re.compile(r'\[([A-Za-z][A-Za-z0-9 .\'-]{0,24})\]\s*("([^"]*)"|“([^”]*)”|([^\[]+))')

# A beat that is ONLY this marker is a held wordless shot: nothing is spoken,
# captions clear, and the sound design carries it (~2.4s + the trailer gap).
SILENCE_RE = re.compile(r"^\s*[(\[]\s*(?:silence|quiet|hold|pause)\s*[)\]]\s*$", re.I)
SILENCE_SECONDS = 2.4

# Emotion cues INSIDE a dialogue line - [Mara] "[whispers] It knows my name."
# ElevenLabs v3 performs them natively; every other voice path strips them
# (they are direction, not words), and they never reach the captions.
_EMO_TAG_RE = re.compile(r"\[[A-Za-z][A-Za-z ']{1,24}\]\s*")
ELEVEN_DIALOGUE_MODEL = "eleven_v3"


def _strip_emotion_tags(text):
    return _EMO_TAG_RE.sub("", text).strip()

# Trailer VO tempo for voices that have no rate knob (ElevenLabs): atempo
# keeps the pitch, word timings are rescaled to match. Edge voices use their
# native rate parameter instead (-15% in trailer mode).
TRAILER_TEMPO = 0.88

# Distinct free edge-tts voices for the character cast, assigned by order of
# first appearance (the narrator's voice is skipped if it collides).
EDGE_CAST = ["en-US-AriaNeural", "en-US-GuyNeural", "en-GB-SoniaNeural",
             "en-US-JennyNeural", "en-GB-RyanNeural", "en-US-AnaNeural"]
# Preferred ElevenLabs premade voices for the cast (matched against the
# account's voice list; any other account voices fill in after).
ELEVEN_CAST_NAMES = ["Rachel", "Josh", "Domi", "Antoni", "Bella", "Charlie"]

# Voices must FIT the character: a Dad with Rachel's voice or a Child with
# Adam's breaks the scene instantly. Kind is inferred from the character's
# tag name + cast look; unknown kinds alternate female/male.
EDGE_CAST_BY_KIND = {
    "male":   ["en-US-GuyNeural", "en-GB-RyanNeural", "en-US-EricNeural",
               "en-US-ChristopherNeural"],
    "female": ["en-US-AriaNeural", "en-US-JennyNeural", "en-GB-SoniaNeural",
               "en-US-MichelleNeural"],
    "child":  ["en-US-AnaNeural", "en-GB-MaisieNeural"],
}
ELEVEN_CAST_BY_KIND = {
    "male":   ["Josh", "Antoni", "Charlie", "Adam", "Callum", "Brian", "Daniel",
               "George", "Eric", "Roger", "Will", "Liam"],
    "female": ["Rachel", "Bella", "Domi", "Matilda", "Sarah", "Laura", "Alice",
               "Jessica", "Lily", "Elli"],
    "child":  ["Gigi", "Lily", "Alice"],   # Gigi is the childlike premade
}

_KIND_WORDS = {
    "child": {"child", "kid", "boy", "girl", "son", "daughter", "toddler",
              "teen", "teenager"},
    "male": {"man", "male", "dad", "father", "mr", "sir", "he", "his", "guy",
             "husband", "brother", "uncle", "grandpa", "grandfather",
             "sheriff", "king", "prince", "gentleman", "priest", "monk"},
    "female": {"woman", "female", "mom", "mother", "mrs", "ms", "she", "her",
               "lady", "wife", "sister", "aunt", "grandma", "grandmother",
               "queen", "princess", "nun", "girl"},
}


def _char_kind(name, look):
    """'male' / 'female' / 'child' / None from a character's tag + cast look
    (whole-word matches only - 'she' must never match inside 'the').
    Child wins over gender: a 'little girl' needs a child voice first."""
    words = set(re.findall(r"[a-z]+", f"{name} {look}".lower()))
    for kind in ("child", "male", "female"):
        if words & _KIND_WORDS[kind]:
            return kind
    return None


def split_dialogue(text):
    """'... [Mara] "Why?" ...' -> [(None, '...'), ('Mara', 'Why?'), (None, '...')].
    Text without markers comes back as a single narrator chunk."""
    chunks, pos = [], 0
    for m in _DLG_RE.finditer(text):
        pre = text[pos:m.start()].strip()
        if pre:
            chunks.append((None, pre))
        line = (m.group(3) or m.group(4) or m.group(5) or "").strip().strip('"“” ')
        if line:
            chunks.append((m.group(1).strip(), line))
        pos = m.end()
    tail = text[pos:].strip()
    if tail:
        chunks.append((None, tail))
    return chunks or [(None, text.strip())]


def strip_dialogue_markup(text):
    """The spoken form of a line: [Name] tags gone, emotion cues gone, the
    quoted words kept - what captions and beat spans line up with."""
    return " ".join((_strip_emotion_tags(t) if sp else t)
                    for sp, t in split_dialogue(text)).strip()


def lipsync_map(ref_dir):
    """{1-based beat index: True} from lipsync.json in the staging dir: beats
    whose staged video's OWN audio is the spoken line (OpenArt talking
    clips). The voice track goes silent there, the clip audio plays instead,
    and captions are estimated across the clip's speech."""
    if not ref_dir:
        return {}
    try:
        data = json.loads((Path(ref_dir) / "lipsync.json").read_text(encoding="utf-8"))
        return {int(k): True for k, v in data.items() if v}
    except Exception:
        return {}


def detect_speech_span(ffmpeg, media, total):
    """(start, end) of the speech region in a clip via silencedetect, for
    caption timing on clip-voiced beats. Falls back to a centered window."""
    try:
        out = run([ffmpeg, "-i", str(Path(media).resolve()),
                   "-af", "silencedetect=noise=-32dB:d=0.2", "-f", "null", "-"])
        log = (out.stderr or "") + (out.stdout or "")
        sil = []
        for m in re.finditer(r"silence_start: ([\d.]+)", log):
            sil.append([float(m.group(1)), total])
        for i, m in enumerate(re.finditer(r"silence_end: ([\d.]+)", log)):
            if i < len(sil):
                sil[i][1] = float(m.group(1))
        # speech regions = complement of the silences
        speech, t = [], 0.0
        for s0, s1 in sil:
            if s0 - t > 0.15:
                speech.append((t, s0))
            t = max(t, s1)
        if total - t > 0.15:
            speech.append((t, total))
        if speech:
            return speech[0][0], speech[-1][1]
    except Exception:
        pass
    return 0.15 * total, 0.9 * total


def synthesize_cast(segments, vconf, out_mp3, tmp, ffmpeg, ffprobe, eleven=None,
                    narrator_tempo=1.0, pad=0.15, clip_voiced=None, cast_info=None):
    """Multi-voice narration for segments carrying [Name] "line" dialogue.
    Synthesizes each chunk with its voice, gives character lines a subtle
    in-scene treatment (thinner low end + a touch of slap echo), stitches
    everything into out_mp3, and returns (words, cast) - words being
    (start, end, word) on the stitched track, same shape as synthesize().
    `eleven` = {key, model, narrator_id, voices} switches the whole cast to
    ElevenLabs; None uses free edge-tts throughout."""
    clip_voiced = clip_voiced or {}
    seg_chunks = [split_dialogue(seg) for seg in segments]
    chunks = [c for sc in seg_chunks for c in sc]
    characters = []
    for sp, _ in chunks:
        if sp and sp not in characters:
            characters.append(sp)

    def look_for(ch):
        """The cast entry's look for a dialogue tag (partial name matches:
        the tag 'Sheriff' finds the cast's 'Sheriff Dade')."""
        chl = ch.lower()
        for c in cast_info or []:
            n = str(c.get("name", "")).lower()
            if n and (n in chl or chl in n):
                return str(c.get("look", ""))
        return ""

    # Kind-aware casting: each character draws from the pool matching their
    # inferred kind (child > male > female); unknowns alternate female/male.
    kinds = {ch: _char_kind(ch, look_for(ch)) for ch in characters}
    unknown_flip = ["female", "male"]
    cast = {}   # character -> (display label, voice)
    if eleven:
        byname = {_voice_base(n): (n.split(" - ")[0].strip(), vid)
                  for n, vid in eleven["voices"].items()}
        leftovers = [v for v in sorted(byname.values())
                     if v[1] != eleven["narrator_id"]]
        used = set()
        for i, ch in enumerate(characters):
            kind = kinds[ch] or unknown_flip[i % 2]
            pool = [byname[w.lower()] for w in ELEVEN_CAST_BY_KIND.get(kind, [])
                    if w.lower() in byname
                    and byname[w.lower()][1] != eleven["narrator_id"]
                    and byname[w.lower()][1] not in used]
            pool += [v for v in leftovers if v[1] not in used and v not in pool]
            cast[ch] = pool[0] if pool else ("narrator", eleven["narrator_id"])
            used.add(cast[ch][1])
    else:
        used = set()
        for i, ch in enumerate(characters):
            kind = kinds[ch] or unknown_flip[i % 2]
            pool = [v for v in EDGE_CAST_BY_KIND.get(kind, [])
                    if v != vconf["voice"] and v not in used]
            pool += [v for v in EDGE_CAST if v != vconf["voice"] and v not in used]
            v = pool[0] if pool else EDGE_CAST[i % len(EDGE_CAST)]
            cast[ch] = (v.split("-")[-1].replace("Neural", ""), v)
            used.add(v)

    # Character lines read hotter than narration: lower stability + style
    # exaggeration gives ElevenLabs dialogue real acting instead of an even
    # narrator read.
    dlg_settings = {"stability": 0.3, "similarity_boost": 0.75,
                    "style": 0.45, "use_speaker_boost": True}
    words, parts, offset = [], [], 0.0
    flat = []   # (chunk, or a clip-voiced segment marker) in timeline order
    for si, sc in enumerate(seg_chunks):
        if si in clip_voiced:
            flat.append(("__clip__", si))
        else:
            flat.extend(sc)
    for idx, (speaker, chunk_text) in enumerate(flat):
        part = tmp / f"vc-{idx:02d}.mp3"
        if speaker == "__clip__":
            # Clip-voiced beat: the staged talking clip IS the spoken line.
            # The voice track holds silence for exactly the clip's length;
            # captions estimate word timings across the clip's speech region,
            # keeping the speaker tag for tint + the — NAME flash.
            si = chunk_text
            vid_path = clip_voiced[si]
            dur = probe_duration(ffprobe, vid_path)
            s0, s1 = detect_speech_span(ffmpeg, vid_path, dur)
            toks = []
            for sp, txt in seg_chunks[si]:
                spoken = _strip_emotion_tags(txt) if sp else txt
                if SILENCE_RE.match(spoken):
                    continue
                toks.extend((wd, sp) for wd in spoken.split())
            span = max(0.5, s1 - s0)
            weight = sum(len(wd) + 1 for wd, _ in toks) or 1
            t = s0
            first = len(words)
            for wd, sp in toks:
                w_d = span * (len(wd) + 1) / weight
                words.append((offset + t, offset + min(t + w_d, s1), wd, sp))
                t += w_d
            if len(words) > first:
                # Anchor the beat span at the CLIP's start, not the speech
                # start - the visual must play from frame 0 or lips shift.
                s, e, wd, sp = words[first]
                words[first] = (offset + 0.02, e, wd, sp)
            wav = tmp / f"vc-{idx:02d}.wav"
            run([ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                 "-t", f"{max(0.5, dur):.3f}", "-c:a", "pcm_s16le", str(wav)])
            parts.append(wav)
            offset += probe_duration(ffprobe, wav)
            continue
        if speaker is None and SILENCE_RE.match(chunk_text):
            # A held wordless shot: pure silence, one invisible word so the
            # beat keeps its time span (and clears the captions while it holds).
            wav = tmp / f"vc-{idx:02d}.wav"
            run([ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                 "-t", str(SILENCE_SECONDS + pad), "-c:a", "pcm_s16le", str(wav)])
            words.append((offset + 0.02, offset + SILENCE_SECONDS, "", None))
            parts.append(wav)
            offset += probe_duration(ffprobe, wav)
            continue
        if eleven:
            vid = eleven["narrator_id"] if speaker is None else cast[speaker][1]
            if speaker is None:
                w = synthesize_elevenlabs(chunk_text, vid, eleven["model"], part,
                                          eleven["key"], settings=eleven.get("settings"))
            else:
                # Dialogue ACTS on the expressive model (v3 performs the
                # [whispers]/[terrified] cues in the line) in Creative mode -
                # stability 0.0 is v3's emotional register; the default reads
                # like an audiobook. If the account can't use v3, fall back
                # to the narration model with hot settings, cues stripped.
                try:
                    w = synthesize_elevenlabs(chunk_text, vid,
                                              eleven.get("dlg_model") or ELEVEN_DIALOGUE_MODEL,
                                              part, eleven["key"],
                                              settings={"stability": 0.0})
                except Exception as exc:
                    print(f"    dialogue model fell back to {eleven['model']} ({str(exc)[:80]})")
                    w = synthesize_elevenlabs(_strip_emotion_tags(chunk_text), vid,
                                              eleven["model"], part, eleven["key"],
                                              settings=dlg_settings)
        elif speaker is None:
            w = asyncio.run(synthesize(chunk_text, vconf, part))
        else:
            w = asyncio.run(synthesize(_strip_emotion_tags(chunk_text),
                                       {"voice": cast[speaker][1],
                                        "rate": "+0%", "pitch": "+0Hz"}, part))
        # Emotion cues are direction, not words: if the alignment carried the
        # bracket tokens (whole or split, e.g. "[nervous" + "laugh]"), keep
        # them out of the captions and the beat spans.
        w = [x for x in w
             if not (str(x[2]).startswith("[") or str(x[2]).endswith("]"))]
        # Normalize every chunk to one wav format so the concat is seamless;
        # dialogue gets the in-scene tone; a short pad keeps a beat of air
        # between speakers (word timings are unaffected - it's trailing).
        filt = f"aresample=44100,aformat=sample_fmts=s16:channel_layouts=mono,apad=pad_dur={pad}"
        if speaker is not None:
            filt = "highpass=f=140,aecho=0.8:0.55:14|29:0.18|0.09," + filt
        elif narrator_tempo != 1.0:
            # Trailer delivery for rate-less voices: slow the narrator only -
            # dialogue keeps its natural pace - and stretch his word timings.
            filt = f"atempo={narrator_tempo}," + filt
            w = [(s / narrator_tempo, e / narrator_tempo, t) for s, e, t in w]
        wav = tmp / f"vc-{idx:02d}.wav"
        run([ffmpeg, "-y", "-i", str(part), "-af", filt, str(wav)])
        # 4-tuples: the speaker rides along so captions can tint dialogue
        # and flash the character's name (None = narrator).
        words.extend((s + offset, e + offset, t, speaker) for s, e, t in w)
        parts.append(wav)
        offset += probe_duration(ffprobe, wav)
    (tmp / "vc-list.txt").write_text("".join(f"file '{p.name}'\n" for p in parts),
                                     encoding="utf-8")
    run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", "vc-list.txt",
         "-c:a", "libmp3lame", "-q:a", "3", str(out_mp3)], cwd=tmp)
    return words, cast


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


def elevenlabs_voice_meta(key):
    """[{name, preview}] for the account's voices - preview is the free sample
    mp3 ElevenLabs hosts per voice (no TTS cost to play)."""
    req = urllib.request.Request(f"{ELEVENLABS_API}/voices",
                                 headers={"xi-api-key": key, "User-Agent": "WhatIfStudio-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return sorted(({"name": v["name"], "preview": v.get("preview_url") or ""}
                   for v in data.get("voices", []) if v.get("voice_id")),
                  key=lambda m: m["name"].lower())


def _voice_base(name):
    """'Adam - Dominant, Firm' -> 'adam' (accounts often carry descriptive suffixes)."""
    return name.split(" - ")[0].strip().lower()


def auto_voice_name(style, voice_names):
    """Which account voice the style mapping would pick (None if no match)."""
    for wanted in ELEVENLABS_VOICE_BY_STYLE.get(style, []):
        for name in voice_names:
            if _voice_base(name) == wanted.lower():
                return name
    return sorted(voice_names)[0] if voice_names else None


def pick_elevenlabs_voice(style, override, key):
    """Resolve a voice: explicit override (name or raw id) beats style mapping."""
    voices = elevenlabs_voices(key)
    if override:
        want = override.strip().lower()
        for name, vid in voices.items():
            if name.lower() == want or _voice_base(name) == want:
                return vid, name
        return override, override      # assume the user passed a raw voice id
    name = auto_voice_name(style, list(voices))
    if name:
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


def synthesize_elevenlabs(text, voice_id, model, mp3_path, key, settings=None):
    """ElevenLabs TTS with character timestamps -> mp3 + per-word timings,
    matching the edge-tts word format so captions/charts work unchanged.
    `settings` overrides voice_settings (trailer mode lowers stability for
    a more dramatic, less even read)."""
    import base64
    url = f"{ELEVENLABS_API}/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128"
    body = json.dumps({
        "text": text,
        "model_id": model,
        "voice_settings": settings or {"stability": 0.5, "similarity_boost": 0.75},
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


def _norm_words(words):
    """Words as 4-tuples (start, end, word, speaker) - the single-voice path
    produces 3-tuples (speaker None), the cast path 4-tuples."""
    return [w if len(w) == 4 else (w[0], w[1], w[2], None) for w in words]


def group_phrases(words, max_words=CAP_MAX_WORDS, max_gap=0.55):
    phrases, cur = [], []
    for start, end, word, speaker in _norm_words(words):
        if cur:
            prev_end = cur[-1][1]
            sentence_break = cur[-1][2].rstrip('"”’').endswith((".", "!", "?", ":", ","))
            # A voice change always starts a fresh phrase, so every caption
            # line belongs to exactly one speaker (clean tint + name flash).
            if (len(cur) >= max_words or (start - prev_end) > max_gap
                    or sentence_break or cur[-1][3] != speaker):
                phrases.append(cur)
                cur = []
        cur.append((start, end, word, speaker))
    if cur:
        phrases.append(cur)
    return phrases


def sanitize_card_text(text):
    """Card text: plain uppercase, no emoji, safe for ASS dialogue."""
    text = re.sub(r"[\U0001F000-\U0001FAFF←-⇿☀-➿️]", "", str(text))
    return re.sub(r"\s+", " ", text).strip().upper()


def words_to_ass(words, pkg=None, total=None):
    """Modern captions: short phrases; the spoken word pops yellow + scales.
    Also lays a title card over the hook and a follow-card over the outro.
    Title/CTA cards use the category's display font and color; the spoken
    captions stay in the caption font for readability."""
    brand = branding_for(pkg)
    _, title_font = brand_font(pkg)
    title_color = brand["title_color"]
    t_sp, t_out, t_sh = brand["title_spacing"], brand["title_outline"], brand["title_shadow"]
    c_out, c_sp = brand["cta_outline"], max(1, brand["title_spacing"] // 2)
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
Style: Title,{title_font},112,{title_color},{title_color},&H00101010,&H90000000,0,0,0,0,100,100,{t_sp},0,1,{t_out},{t_sh},8,70,70,360,1
Style: CTA,{title_font},62,{CAP_WHITE},{CAP_WHITE},&H00101010,&H90000000,0,0,0,0,100,100,{c_sp},0,1,{c_out},2,8,90,90,430,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Flatten to one caption event per word so we can butt each event exactly
    # against the next (no overlap, no gap -> no doubled/garbled frames).
    # Dialogue phrases (speaker-tagged words from synthesize_cast) render in
    # the character's tint + italics; group_phrases never mixes speakers.
    phrases = group_phrases(words)
    tints = {}
    for ph in phrases:
        sp = ph[0][3]
        if sp and sp not in tints:
            tints[sp] = CAP_SPEAKER_TINTS[len(tints) % len(CAP_SPEAKER_TINTS)]
    events = []
    for phrase in phrases:
        spk = phrase[0][3]
        base = tints.get(spk, CAP_WHITE)
        for k, (start, _, _, _) in enumerate(phrase):
            parts = []
            for j, (_, _, w, _) in enumerate(phrase):
                token = w.upper()
                parts.append(f"{{\\c{CAP_HL}}}{token}{{\\c{base}}}" if j == k else token)
            tags = f"\\an5\\pos({WIDTH // 2},{CAP_Y})"
            if spk:
                tags += f"\\i1\\c{base}"
            if k == 0:  # entrance pop only when a new phrase appears
                tags += "\\fad(70,0)\\fscx78\\fscy78\\t(0,120,\\fscx100\\fscy100)"
            events.append([start, f"{{{tags}}}" + " ".join(parts)])

    lines = []
    for i, (start, text) in enumerate(events):
        end = events[i + 1][0] if i + 1 < len(events) else start + 0.6
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Cap,,0,0,0,,{text}")

    # A "— NAME" flash above the captions whenever a character starts
    # speaking, in their tint, so viewers track who's talking over fast cuts.
    runs = []
    for ph in phrases:
        sp = ph[0][3]
        if runs and runs[-1][0] == sp:
            runs[-1][2] = ph[-1][1]
        else:
            runs.append([sp, ph[0][0], ph[-1][1]])
    for sp, s, e in runs:
        if not sp:
            continue
        name = sanitize_card_text(sp)
        dur = min(1.4, max(0.7, e - s))
        tag = (f"{{\\an5\\pos({WIDTH // 2},{CAP_Y - 108})\\fs54\\c{tints[sp]}"
               "\\fad(80,120)}")
        lines.append(f"Dialogue: 1,{ass_time(s)},{ass_time(s + dur)},Cap,,0,0,0,,{tag}— {name}")

    if pkg:
        title = sanitize_card_text((pkg.get("thumbnails") or [pkg.get("title", "")])[0])
        if title:
            fx = r"{\fad(120,200)\fscx80\fscy80\t(0,150,\fscx100\fscy100)}"
            lines.append(f"Dialogue: 1,{ass_time(0)},{ass_time(TITLE_SECONDS)},Title,,0,0,0,,{fx}{title}")
    if total and total > 12:
        cta_start = max(0.0, total - CTA_SECONDS)
        fx = r"{\fad(250,0)}"
        lines.append(f"Dialogue: 1,{ass_time(cta_start)},{ass_time(total + 0.3)},CTA,,0,0,0,,{fx}{branding_for(pkg)['cta']}")

    return header + "\n".join(lines) + "\n"


# ---------------------------------------------------------------- AI visuals


# Most short-form content works better with humans in frame ("reenactments").
# When a shot description has no people, one is added - disable with --no-people.
PEOPLE_BIAS = True
_PERSON_RE = re.compile(
    r"\b(person|people|man|men|woman|women|human|humans|hand|hands|face|faces|figure|silhouette|"
    r"crowd|narrator|kid|kids|child|children|family|friend|someone|somebody|guy|girl|boy|"
    r"commuter|farmer|scientist|worker|villager|audience|viewer|couple|stranger|player|character|"
    r"you|body|eyes|portrait)\b", re.I)
HUMAN_HINT = "a real person on camera acting out the moment, natural expression"


def _shot_for_segment(seg_index, seg_count, shot_count):
    return min(round(seg_index * (shot_count - 1) / max(1, seg_count - 1)), shot_count - 1)


def _raw_shot_text(pkg, seg_index, seg_count):
    """The cleaned shot/beat description for one narration segment.
    When there are fewer shots than segments, only the FIRST segment mapped to
    a shot uses it - later ones fall back to their own narration beat, so
    every prompt is unique and matched to what's being said."""
    shots = pkg.get("shotList") or [pkg.get("premise", pkg.get("title", "abstract scene"))]
    pick = _shot_for_segment(seg_index, seg_count, len(shots))
    first_claimant = next(j for j in range(seg_count)
                          if _shot_for_segment(j, seg_count, len(shots)) == pick)
    if seg_index == first_claimant:
        src = shots[pick]
    else:
        beats = pkg.get("beats") or []
        src = beats[seg_index - 1] if 1 <= seg_index <= len(beats) else shots[pick]
    if SILENCE_RE.match(str(src)):
        # A silent hold still needs a picture: a wordless static frame of
        # the story's world (writers usually replace this with a real shot).
        src = f"{shots[pick]}, a held static frame, nothing moves, unsettling stillness"
    src = re.sub(r"^[A-Za-z /-]{2,20}:", "", src)                      # "Hook:" style prefixes
    src = re.sub(r"\[[A-Za-z][A-Za-z0-9 .'-]{0,24}\]", "", src)        # [Name] dialogue tags
    src = re.sub(r"[\"“”‘’']", "", src)
    # Drop instructions about on-screen text - generated text comes out garbled.
    src = re.sub(r"\b(labeled|labelled|stamped|caption|chyron|lower.third|overlay|typed|on.screen text)\b[^,.;]*",
                 "", src, flags=re.I)
    return re.sub(r"\s+", " ", src).strip(" ,.;-")


# ------------------------------------------------- prompt polish (OpenAI)
# With an OpenAI key configured, every scenario's per-beat visual prompts are
# rewritten ONCE into richer cinematic directions (subject + action, setting,
# camera, mood) and cached on disk - so re-renders cost nothing and the
# Produce page's copy-paste prompts match what a render would generate.
# No key = raw shot prompts, exactly as before. Disable with --no-polish.

OPENAI_API = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"
POLISH_PROMPTS = True
POLISH_CACHE = Path(__file__).resolve().parent / "polished-prompts"
_polish_memo = {}


def openai_key():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    f = Path(__file__).resolve().parent / "openai_key.txt"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    return None


def _polish_via_openai(pkg, seg_count, key):
    title = pkg.get("title", "a what-if scenario")
    notes = "\n".join(f"Clip {i + 1}: {_raw_shot_text(pkg, i, seg_count)}"
                      for i in range(seg_count))
    people_rule = (
        "Put a specific relatable person doing something concrete in nearly every "
        "prompt (reenactment style)." if PEOPLE_BIAS else
        "Include people only where a clip note calls for them.")
    cast = pkg.get("cast") or []
    cast_rule = ("Recurring characters: every clip is generated independently, so "
                 "whenever one of these characters appears, describe them with "
                 "EXACTLY this look, word for word: "
                 + "; ".join(f'{c.get("name")} = {c.get("look")}' for c in cast)
                 + ". " if cast else "")
    style_rule = ""
    if (pkg.get("category") or "") == "Scary Story":
        # Quiet-horror cinematography (the social-thriller school): the frame
        # itself should unsettle, one composition device per clip, no repeats.
        style_rule = (
            "This is QUIET HORROR - compose unsettling frames the way social-thriller "
            "films do. Use a DIFFERENT one of these devices per clip: dead-centered "
            "symmetrical framing; a subject looking directly into the camera, expression "
            "a little too calm; a wide static frame of an ordinary place with one small "
            "detail wrong; a figure standing unnaturally still, or slightly too far away; "
            "a long hallway or doorway with heavy negative space; something mundane in "
            "bright cheerful daylight that feels deeply wrong. Stillness over action, "
            "unease over gore. ")
    prompt = (
        "You write prompts for AI image/video generators. "
        f'The clips below form one vertical 9:16 short answering: "{title}". '
        "Rewrite each clip note into ONE vivid visual prompt of 15-35 words: a concrete "
        "subject and action, the setting, a camera angle or movement, and lighting/mood. "
        "Stay true to the moment each note describes - same scene, richer picture - and "
        "keep a consistent visual world across all clips. " + cast_rule + style_rule + people_rule + " "
        "Never mention on-screen text, captions, words, letters, numbers, signs, logos or "
        "watermarks. Reply with ONLY minified JSON, no markdown fences: "
        f'{{"prompts":["...", ...]}} with exactly {seg_count} strings in clip order.\n'
        + notes)
    body = json.dumps({
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.8,
        "max_tokens": 120 * seg_count + 100,
    }).encode("utf-8")
    req = urllib.request.Request(OPENAI_API, data=body, method="POST", headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "WhatIfStudio-pipeline/1.0",
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        reply = json.loads(resp.read().decode("utf-8", "replace"))
    record_spend("openai", "prompt polish", openai_usage_cost(reply),
                 OPENAI_MODEL, pkg.get("scenarioId", ""), estimated=True)
    data = json.loads(reply["choices"][0]["message"]["content"])
    prompts = [re.sub(r"\s+", " ", str(p)).strip(" ,.;") for p in (data.get("prompts") or [])]
    if len(prompts) != seg_count or not all(prompts):
        raise RuntimeError(f"expected {seg_count} prompts, got {len(prompts)}")
    return prompts


def polished_shot_texts(pkg, seg_count):
    """Polished per-beat prompts for a scenario, or None (no key / disabled /
    call failed) - callers then fall back to the raw shot text."""
    if not POLISH_PROMPTS:
        return None
    memo_key = (pkg.get("scenarioId", "pkg"), seg_count, PEOPLE_BIAS)
    if memo_key in _polish_memo:
        return _polish_memo[memo_key]
    result = None
    cache = POLISH_CACHE / (f"{slugify(str(memo_key[0]))}-{seg_count}seg"
                            f"{'' if PEOPLE_BIAS else '-nopeople'}.json")
    try:
        cached = json.loads(cache.read_text(encoding="utf-8"))
        if isinstance(cached, list) and len(cached) == seg_count:
            result = [str(p) for p in cached]
    except Exception:
        pass
    if result is None and openai_key():
        try:
            result = _polish_via_openai(pkg, seg_count, openai_key())
            POLISH_CACHE.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(result, indent=1), encoding="utf-8")
            print(f"    prompts polished by OpenAI -> {cache.name}")
        except Exception as exc:
            print(f"    prompt polish failed ({exc}) - using raw shot prompts")
    _polish_memo[memo_key] = result
    return result


def _apply_cast(text, cast):
    """Pin recurring characters into a prompt: the first mention of a cast
    name gains their look - 'Mara' -> 'Mara (mid-30s, red parka)' - so every
    independently generated clip draws the same person. Skipped when the
    look is already in the text (e.g. the polish pass wrote it out)."""
    low = text.lower()
    for c in cast or []:
        name, look = str(c.get("name", "")), str(c.get("look", ""))
        if not name or not look:
            continue
        # Any two consecutive look-words already in the text means the look
        # is (at least partly) written out - don't describe her twice.
        lw = re.sub(r"[^a-z0-9 -]", "", look.lower()).split()
        if any(f"{a} {b}" in low for a, b in zip(lw, lw[1:])):
            continue
        text = re.sub(rf"\b{re.escape(name)}\b", f"{name} ({look})", text, count=1)
    return text


def ai_prompt_for_segment(pkg, seg_index, seg_count, style_suffix):
    """Build an image/video prompt for one narration segment: the OpenAI-polished
    version when available, otherwise the raw shot/beat text (+ people bias).
    Either way, cast characters keep their exact look in every prompt."""
    polished = polished_shot_texts(pkg, seg_count)
    if polished:
        core = polished[seg_index]
    else:
        core = _raw_shot_text(pkg, seg_index, seg_count)
        if PEOPLE_BIAS and not _PERSON_RE.search(core):
            core = f"{core}, {HUMAN_HINT}"
    return f"{_apply_cast(core, pkg.get('cast'))}, {style_suffix}"


def fetch_ai_image(prompt, dest, seed):
    url = (AI_IMAGE_HOST + urllib.parse.quote(prompt)
           + f"?width={WIDTH}&height={HEIGHT}&nologo=true&seed={seed}")
    req = urllib.request.Request(url, headers={"User-Agent": "WhatIfStudio-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=180) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out)
    if dest.stat().st_size < 5000:
        dest.unlink(missing_ok=True)
        raise RuntimeError("image response too small")


def generate_ai_visuals(pkg, seg_count, style_key, cache_root, mood=None):
    """One generated image per narration segment, cached per scenario+style."""
    suffix = styled_suffix(AI_STYLES[style_key], mood)
    folder = Path(cache_root) / f"{pkg.get('scenarioId', 'pkg')}-{style_key}"
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    for i in range(seg_count):
        dest = folder / f"{i + 1:02d}.jpg"
        if not dest.exists():
            prompt = ai_prompt_for_segment(pkg, i, seg_count, suffix)
            for attempt in range(4):
                try:
                    fetch_ai_image(prompt, dest, seed=(i + 1) * 13 + attempt * 101)
                    print(f"    image {i + 1}/{seg_count} generated")
                    break
                except Exception as exc:
                    # The free service rate-limits per IP (429) - a render can
                    # afford to wait out the window; a 3s retry burst can't.
                    throttled = isinstance(exc, urllib.error.HTTPError) and exc.code == 429
                    if attempt == 3:
                        print(f"    image {i + 1}/{seg_count} FAILED ({exc}) - neighbors will fill in")
                    else:
                        time.sleep(25 if throttled else 3)
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
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        # Surface the provider's error body - "403 Forbidden" alone is undiagnosable.
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {exc.code}: {detail or exc.reason}") from None
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


# ------------------------------------------------- spend ledger
# Every metered API call appends one entry so the Spend page can total real
# money: tryinfer prices come straight from the provider's usage block;
# OpenAI entries are estimates computed from token counts.

SPEND_LEDGER = Path(__file__).resolve().parent / "spend-ledger.json"


def openart_usd_per_credit():
    """USD per OpenArt credit, for spend ESTIMATES only. Defaults to the
    Essential plan's effective rate (~$14 / 4000 credits); put one number in
    pipeline/openart_rate.txt to override."""
    try:
        return float((Path(__file__).resolve().parent / "openart_rate.txt")
                     .read_text(encoding="utf-8").strip())
    except Exception:
        return 14.0 / 4000.0


def record_spend(service, kind, price_usd, model="", scenario="", estimated=False,
                 credits=None):
    """Append one paid event to the ledger. Never raises - a bookkeeping
    failure must not break a render. `credits` records an OpenArt charge in
    its native unit; the USD figure is then estimated at the plan rate."""
    try:
        if price_usd is None and credits is not None:
            price_usd = float(credits) * openart_usd_per_credit()
            estimated = True
        if price_usd is None:
            return
        entries = []
        try:
            entries = json.loads(SPEND_LEDGER.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                entries = []
        except Exception:
            pass
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "service": service, "kind": kind, "model": model,
            "scenario": scenario, "price_usd": round(float(price_usd), 6),
            "estimated": bool(estimated),
        }
        if credits is not None:
            entry["credits"] = int(round(float(credits)))
        entries.append(entry)
        SPEND_LEDGER.write_text(json.dumps(entries, indent=1), encoding="utf-8")
    except Exception:
        pass


# OpenAI gpt-4o-mini list prices per 1M tokens (for spend *estimates* only).
OPENAI_PRICE_IN = 0.15 / 1e6
OPENAI_PRICE_OUT = 0.60 / 1e6


def openai_usage_cost(reply):
    """Estimated dollars for one chat-completions reply, from its usage block."""
    u = (reply or {}).get("usage") or {}
    try:
        return u.get("prompt_tokens", 0) * OPENAI_PRICE_IN + u.get("completion_tokens", 0) * OPENAI_PRICE_OUT
    except TypeError:
        return None


_IMAGE_EXT_RE = re.compile(r"\.(jpe?g|png|webp)(\?|$)", re.I)


def _find_image_url(obj, in_images=False):
    """Find the finished image URL anywhere in the poll response. Some models
    return presigned S3 URLs with no file extension inside an "images" list
    ({"output": {"images": [{"url": ...}]}}) - anything under an images/image
    key is trusted without the extension check."""
    if isinstance(obj, str):
        return obj if obj.startswith("http") and (_IMAGE_EXT_RE.search(obj) or in_images) else None
    if isinstance(obj, dict):
        for key in ("image_url", "url", "output_url", "download_url", "result_url"):
            v = obj.get(key)
            if isinstance(v, str) and v.startswith("http") \
                    and (_IMAGE_EXT_RE.search(v) or key != "url" or in_images):
                return v
        for k, v in obj.items():
            found = _find_image_url(v, in_images or k in ("images", "image"))
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_image_url(v, in_images)
            if found:
                return found
    return None


def infer_list_models(key):
    """The tryinfer catalog: [{model_id, capability, ...}] (discovered live,
    so new models appear without a code change)."""
    req = urllib.request.Request(f"{INFER_BASE}/inference/models",
                                 headers={"Authorization": f"Bearer {key}",
                                          "User-Agent": "WhatIfStudio-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return [m for m in data.get("models", []) if m.get("model_id")]


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


def _run_infer_job(model, task, input_obj, key, find_url=_find_video_url):
    """Submit one job and poll to a terminal state. Returns (url, price, error)."""
    rid = infer_submit(model, task, input_obj, key)
    waited = 0
    while waited < INFER_POLL_TIMEOUT:
        time.sleep(INFER_POLL_INTERVAL)
        waited += INFER_POLL_INTERVAL
        resp = infer_poll(rid, key)
        status = _find_status(resp)
        if status in ("COMPLETED", "SUCCEEDED", "SUCCESS"):
            url = find_url(resp)
            if not url:
                return None, None, "completed but no output URL: " + json.dumps(resp)[:400]
            return url, _find_price(resp), None
        if status in ("FAILED", "ERROR", "CANCELLED", "CANCELED"):
            err = json.dumps((resp or {}).get("error") or resp)[:300]
            return None, None, f"{status}: {err}"
    return None, None, f"timed out after {INFER_POLL_TIMEOUT}s"


def _ref_frame(ref_dir, index):
    """A user-staged reference image for one beat (ref-NN.jpg beside the
    staged clips, uploaded on the Produce page), or None."""
    if not ref_dir:
        return None
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        f = Path(ref_dir) / f"ref-{index:02d}{ext}"
        if f.is_file():
            return f
    return None


def _ref_video(ref_dir, index):
    """A user-staged reference video for one beat (refv-NN.mp4), or None."""
    if not ref_dir:
        return None
    f = Path(ref_dir) / f"refv-{index:02d}.mp4"
    return f if f.is_file() else None


def _ref_choice(ref_dir, index):
    """Which per-beat reference is active: 'video', 'image', or None.
    The Produce page's radio buttons write ref-choice.json; without an entry,
    whichever file exists wins (image when both do)."""
    img, vid = _ref_frame(ref_dir, index), _ref_video(ref_dir, index)
    if not img and not vid:
        return None
    choice = ""
    try:
        choice = json.loads((Path(ref_dir) / "ref-choice.json")
                            .read_text(encoding="utf-8")).get(str(index), "")
    except Exception:
        pass
    if choice == "video" and vid:
        return "video"
    if choice == "image" and img:
        return "image"
    return "image" if img else "video"


def _ref_frame_uri(ref, ffmpeg, cache_folder, index):
    """The reference image as a base64 data URI for image-to-video. When
    ffmpeg is available the image is first normalized to the clip's own
    9:16 1080x1920 frame (cached; redone when the image changes) so the
    model isn't handed a mismatched aspect ratio."""
    src = ref
    if ffmpeg:
        norm = cache_folder / f"ref-{index:02d}-norm.jpg"
        if not norm.exists() or norm.stat().st_mtime < ref.stat().st_mtime:
            try:
                run([ffmpeg, "-y", "-i", str(ref),
                     "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT}",
                     "-frames:v", "1", "-q:v", "3", str(norm)])
            except Exception:
                norm = None
        if norm and norm.is_file():
            src = norm
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp"}[src.suffix.lower()]
    return f"data:{mime};base64,{base64.b64encode(src.read_bytes()).decode('ascii')}"


def generate_infer_videos(pkg, segments, key, model, task, duration, cache_root,
                          ref_dir=None, ffmpeg=None, mood=None):
    """One AI-generated clip per beat via tryinfer. image-to-video animates the
    beat's user-attached reference image when one is staged (ref-NN.jpg in
    ref_dir), else a free Pollinations first frame (shared style = coherence);
    if the provider rejects that image, the beat falls back to text-to-video.
    Clips cache per scenario+model; a beat regenerates when its reference
    image is newer than its cached clip. Paid API - one billed job per beat."""
    folder = Path(cache_root) / f"{slugify(pkg.get('scenarioId', 'pkg'))}-{model}"
    folder.mkdir(parents=True, exist_ok=True)
    files, spent = [], 0.0
    for i, seg in enumerate(segments):
        if _ref_choice(ref_dir, i + 1) == "video":
            vid = _ref_video(ref_dir, i + 1)
            print(f"    beat {i + 1}: using your uploaded video ({vid.name}) - nothing billed")
            files.append(vid)
            continue
        dest = folder / f"{i + 1:02d}.mp4"
        ref = _ref_frame(ref_dir, i + 1)
        if dest.exists():
            if ref and ref.stat().st_mtime > dest.stat().st_mtime:
                print(f"    beat {i + 1}: reference image is newer than the cached clip - regenerating")
                dest.unlink()
            else:
                files.append(dest)
                continue
        motion = ai_prompt_for_segment(pkg, i, len(segments),
                                       styled_suffix(VIDEO_MOTION_SUFFIX, mood))
        base_input = {"prompt": motion, "duration_seconds": str(duration), "aspect_ratio": "9:16"}

        attempts = []
        if task == "image-to-video":
            if ref:
                try:
                    uri = _ref_frame_uri(ref, ffmpeg, folder, i + 1)
                    attempts.append(("image-to-video", {**base_input, "image_url": uri}))
                    print(f"    beat {i + 1}: animating your attached image ({ref.name})")
                except Exception as exc:
                    print(f"    beat {i + 1}: couldn't read attached image ({exc})")
            frame_prompt = ai_prompt_for_segment(
                pkg, i, len(segments), styled_suffix(AI_STYLES[branding_for(pkg)["style"]], mood))
            image_url = pollinations_image_url(frame_prompt, seed=(i + 1) * 17)
            if _prewarm_url(image_url):
                attempts.append(("image-to-video", {**base_input, "image_url": image_url}))
            elif not attempts:
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
                record_spend("tryinfer", "video clip", price, model, pkg.get("scenarioId", ""))
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


def generate_infer_images(pkg, seg_count, key, model, style_key, cache_root, mood=None):
    """One paid AI image per beat via tryinfer text-to-image (cheaper than
    video; Ken Burns motion is added at assembly like any still). Uses the
    same polished prompts and style suffixes as the free image path. Images
    cache per scenario+model - re-renders are free."""
    suffix = styled_suffix(AI_STYLES.get(style_key, AI_STYLES["cinematic"]), mood)
    folder = Path(cache_root) / f"{slugify(pkg.get('scenarioId', 'pkg'))}-{slugify(model)}"
    folder.mkdir(parents=True, exist_ok=True)
    files, spent = [], 0.0
    for i in range(seg_count):
        dest = folder / f"{i + 1:02d}.jpg"
        if dest.exists():
            files.append(dest)
            continue
        prompt = ai_prompt_for_segment(pkg, i, seg_count, suffix)
        try:
            url, price, err = _run_infer_job(model, "text-to-image",
                                             {"prompt": prompt, "aspect_ratio": "9:16"},
                                             key, find_url=_find_image_url)
        except Exception as exc:
            url, price, err = None, None, str(exc)
        if not url:
            # One bad beat (moderation, model hiccup) shouldn't leave a hole:
            # fall back to a free Pollinations image so the beat keeps ITS
            # visual; only if that fails too do neighbors fill in.
            try:
                fetch_ai_image(prompt, dest, seed=(i + 1) * 13)
                print(f"    image {i + 1}/{seg_count} failed ({str(err)[:160]}) - used a free Pollinations image instead")
                files.append(dest)
            except Exception:
                print(f"    image {i + 1}/{seg_count} failed: {err} - neighbors will fill in")
            continue
        try:
            dl = urllib.request.Request(url, headers={"User-Agent": "WhatIfStudio-pipeline/1.0"})
            with urllib.request.urlopen(dl, timeout=180) as resp, open(dest, "wb") as out:
                shutil.copyfileobj(resp, out)
            if dest.stat().st_size < 5000:
                dest.unlink(missing_ok=True)
                raise RuntimeError("downloaded image too small")
        except Exception as exc:
            print(f"    image {i + 1}/{seg_count} download failed: {exc}")
            continue
        spent += price or 0.0
        record_spend("tryinfer", "image", price, model, pkg.get("scenarioId", ""))
        price_note = f" (${price:.3f})" if price is not None else ""
        print(f"    image {i + 1}/{seg_count}: done via {model}{price_note}")
        files.append(dest)
    print(f"    AI-image spend this run: ${spent:.2f}")
    if not files:
        raise RuntimeError("no AI images produced (check key, model name, and credits)")
    return files


# ---------------------------------------------------------------- visuals


def probe_duration(ffprobe, media_path):
    out = run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(media_path)])
    return float(out.stdout.strip())


# ---------------------------------------------------------------- beat SFX

SFX_RATE = 48000


def synth_reveal_sfx(path, riser=3.0, tail=2.2):
    """Write a mono WAV: a sub-bass riser (rising sine sweep + hushed noise)
    that swells for `riser` seconds, then a soft low impact that decays over
    `tail` seconds. Synthesized from scratch - no samples, nothing to license.
    The impact lands exactly at t=riser, so callers align that moment with
    the first word of the reveal beat."""
    n_riser = int(riser * SFX_RATE)
    n_tail = int(tail * SFX_RATE)
    rng = random.Random(333)          # deterministic: same render, same sound
    out = array.array("h", bytes(2 * (n_riser + n_tail)))

    phase, lp = 0.0, 0.0
    for i in range(n_riser):
        t = i / SFX_RATE
        prog = t / riser
        freq = 30.0 * (54.0 / 30.0) ** prog          # 30 Hz sweeping up to ~54 Hz
        phase += 2.0 * math.pi * freq / SFX_RATE
        lp += 0.015 * (rng.uniform(-1, 1) - lp)      # one-pole lowpassed rumble
        amp = 0.22 * prog * prog
        out[i] = int(32767 * max(-1.0, min(1.0, amp * (math.sin(phase) + 1.4 * lp))))

    for i in range(n_tail):
        t = i / SFX_RATE
        freq = 40.0 + 12.0 * math.exp(-4.0 * t)      # pitch sags as it decays
        phase += 2.0 * math.pi * freq / SFX_RATE
        thump = 0.10 * math.exp(-90.0 * t) * rng.uniform(-1, 1)   # 25ms attack noise
        amp = 0.38 * math.exp(-2.4 * t)
        out[n_riser + i] = int(32767 * max(-1.0, min(1.0, amp * math.sin(phase) + thump)))

    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SFX_RATE)
        w.writeframes(out.tobytes())


DREAD_RATE = 24000   # rumble + metallic highs live well below 12 kHz


def synth_dread_bed(path, duration, seed=911, climax=None):
    """Write a mono WAV bed of unsettling sound design in the American Horror
    Story / Whisper Man trailer school: the SAME few motifs cycling - a
    detuned sub drone, a double heartbeat, breath-like noise swells, sparse
    metallic shrieks - but everything ESCALATES toward `climax` (default 85%
    in; callers pass the reveal time): the heartbeat accelerates, the drone
    beats faster and swells, the shrieks come closer together and hotter,
    and the whole master rises. Synthesized from scratch - no samples,
    nothing to license. Deterministic per seed."""
    climax = min(duration, climax or 0.85 * duration)
    n = int(duration * DREAD_RATE)
    rng = random.Random(seed)
    two_pi = 2.0 * math.pi

    def esc(t):   # escalation 0..1, eased so the build back-loads
        return min(1.0, max(0.0, t / climax)) ** 1.4

    buf = array.array("f", bytes(4 * n))
    # Base layer per-sample: drone (detune widens + swells) and breaths.
    ph1 = ph2 = 0.0
    lp = 0.0
    for i in range(n):
        t = i / DREAD_RATE
        e = esc(t)
        ph1 += two_pi * 48.0 / DREAD_RATE
        ph2 += two_pi * (48.7 + 0.9 * e) / DREAD_RATE
        a = (0.16 * (1.0 + 0.8 * e) * (math.sin(ph1) + math.sin(ph2))
             * (0.65 + 0.35 * math.sin(two_pi * t / 13.0)))
        lp += 0.03 * (rng.uniform(-1, 1) - lp)
        a += lp * (1.5 + 1.2 * e) * max(0.0, math.sin(two_pi * t / 7.0 - 1.2)) ** 3
        buf[i] = a
    # Heartbeat: an accelerating clock (1.6 s apart -> ~1.05 s at the climax),
    # each beat a double thump that also hits harder as it builds.
    hb_len = int(0.2 * DREAD_RATE)
    t = 0.4
    while t < duration:
        e = esc(t)
        for off in (0.0, 0.24 - 0.06 * e):
            i0 = int((t + off) * DREAD_RATE)
            for j in range(min(hb_len, n - i0)):
                d = j / DREAD_RATE
                buf[i0 + j] += (0.34 + 0.22 * e) * math.exp(-d * 26.0) * math.sin(two_pi * 52.0 * d)
        t += 1.6 - 0.55 * e
    # Metallic shrieks: sparse early, closing in and heating up near the climax.
    sh_len = int(2.4 * DREAD_RATE)
    t = 3.0
    while t < duration - 1.5:
        e = esc(t)
        gain = (0.14 + 0.14 * e) * rng.uniform(0.8, 1.1)
        base = rng.choice((1490.0, 1730.0, 2090.0))
        i0 = int(t * DREAD_RATE)
        for j in range(min(sh_len, n - i0)):
            d = j / DREAD_RATE
            env = min(1.0, d / 0.3) * math.exp(-d * 1.7) * gain
            buf[i0 + j] += env * (math.sin(two_pi * base * d)
                                  + 0.7 * math.sin(two_pi * base * 1.38 * d)
                                  + 0.5 * math.sin(two_pi * base * 1.83 * d))
        t += max(1.6, rng.uniform(6.5, 10.0) - e * rng.uniform(3.5, 5.5))
    # Master: the whole bed rises into the climax. Hotter than a typical
    # music bed - this IS the soundtrack.
    out = array.array("h", bytes(2 * n))
    for i in range(n):
        g = 1.15 * (0.78 + 0.5 * esc(i / DREAD_RATE))
        out[i] = int(32767 * max(-1.0, min(1.0, buf[i] * g)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(DREAD_RATE)
        w.writeframes(out.tobytes())


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


def has_audio(ffprobe, media_path):
    out = run([ffprobe, "-v", "error", "-select_streams", "a", "-show_entries",
               "stream=codec_type", "-of", "csv=p=0", str(Path(media_path).resolve())])
    return "audio" in out.stdout


def render_segment_clip(ffmpeg, visual, duration, out_path, index=0, chart=None, font_ff=None, cwd=None,
                        keep_audio=False, ffprobe=None):
    """Scale/crop one visual to a full-frame vertical clip of the given length.
    Still images get an alternating camera move (in / pan / out / pan back).
    If a chart spec is given, an animated counter/bar is overlaid.
    `keep_audio` preserves the clip's own sound (models like LTX generate
    ambience) - segments without sound get a silent track so concat stays
    uniform. `cwd` lets the chart drawtext reference the font by bare
    filename, avoiding the Windows drive-letter colon that breaks ffmpeg's
    filtergraph parser."""
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

    cmd = [ffmpeg, "-y", *loop, "-i", str(Path(visual).resolve())]
    audio_args = ["-an"]
    if keep_audio:
        if visual.suffix.lower() in VIDEO_EXTS and ffprobe and has_audio(ffprobe, visual):
            audio_args = ["-map", "0:v", "-map", "0:a", "-af", "apad", "-c:a", "aac", "-b:a", "160k"]
        else:
            cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
            audio_args = ["-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "160k"]
    cmd += ["-t", f"{duration:.2f}", "-vf", vf, *audio_args,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out_path)]
    run(cmd, cwd=cwd)


def build_clip_base(ffmpeg, visuals, spans, tmp, charts=None, font_ff=None, keep_audio=False, ffprobe=None,
                    audio_gains=None):
    """One clip per beat with alternating motion, joined by crossfades.
    Segments before the last are rendered XFADE_DUR longer so the fades
    consume the extra tail and the visual timeline stays in sync with audio.
    `charts` (aligned to spans) overlays an animated number on chart beats.
    With `keep_audio`, each segment's sound is trimmed to its exact span and
    hard-concatenated, so the ambience track stays aligned with the voice.
    `audio_gains` (aligned to spans) sets a per-beat volume - clip-voiced
    beats play their own audio at 1.0 while the rest follow --clip-audio."""
    if audio_gains is not None:
        keep_audio = any(g > 0 for g in audio_gains)
    durs = [round(max(0.4, end - start), 2) for start, end in spans]
    seg_files = []
    for i, dur in enumerate(durs):
        seg = tmp / f"seg_{i:02d}.mp4"
        extra = XFADE_DUR if i < len(durs) - 1 else 0.5
        chart = charts[i] if charts and i < len(charts) else None
        render_segment_clip(ffmpeg, visuals[i % len(visuals)], dur + extra, seg, index=i,
                            chart=chart, font_ff=font_ff, cwd=tmp,
                            keep_audio=keep_audio, ffprobe=ffprobe)
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
    maps = ["-map", prev]
    codecs = []
    if keep_audio:
        for i, d in enumerate(durs):
            g = (audio_gains[i] if audio_gains is not None and i < len(audio_gains) else 1.0)
            chain.append(f"[{i}:a]atrim=0:{d},asetpts=PTS-STARTPTS,volume={g:.2f}[a{i}]")
        chain.append("".join(f"[a{i}]" for i in range(len(durs))) + f"concat=n={len(durs)}:v=0:a=1[aout]")
        maps += ["-map", "[aout]"]
        codecs = ["-c:a", "aac", "-b:a", "160k"]
    run([ffmpeg, "-y", *inputs, "-filter_complex", ";".join(chain), *maps,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", *codecs, "base.mp4"], cwd=tmp)
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
    with no captions or counters. Ready to upload as the video's thumbnail.
    Uses the category's display font (already copied to tmp) and color."""
    brand_path, _ = brand_font(pkg)
    if brand_path:
        font_ff = brand_path.name
    thumb_color = branding_for(pkg)["thumb_color"]
    # The cover carries the FULL title: scrollers should know what the video
    # is without reading the platform caption.
    text = sanitize_card_text(pkg.get("title", "") or (pkg.get("thumbnails") or [""])[0])
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > 18:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    lines = lines[:5]
    fontsize = {1: 128, 2: 106, 3: 88, 4: 74}.get(len(lines), 64)
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
            f"fontcolor={thumb_color}:borderw={branding_for(pkg)['thumb_border']}:bordercolor=black:x=(w-tw)/2:y={start_y + i * line_h}"
        )
    run([ffmpeg, "-y", *inp, "-frames:v", "1", "-vf", ",".join(filters), "-q:v", "3",
         str(out_path)], cwd=tmp)


def speech_intervals(words, pad=0.12, gap=0.35):
    """Merged (start, end) spans where someone is speaking - drives the
    music ducking so lines sit clearly on top of the score."""
    spans = []
    for w in words:
        if not str(w[2]).strip():
            continue   # silence placeholders aren't speech
        s, e = max(0.0, w[0] - pad), w[1] + pad
        if spans and s - spans[-1][1] <= gap:
            spans[-1][1] = max(spans[-1][1], e)
        else:
            spans.append([s, e])
    return spans


def final_render(ffmpeg, base, pkg, total, has_music, out_path, tmp, clip_audio=0.0,
                 sfx_delay_ms=None, duck=None, music_vol=None, swell=None):
    """Overlay captions and mix audio onto the base video (or a gradient).
    `clip_audio` > 0 mixes the base video's own sound (e.g. LTX-generated
    ambience) under the voice at that volume. `sfx_delay_ms` places tmp's
    sfx.wav on the timeline (None = no beat SFX). `duck` = speech spans:
    the music dips to ~30% while anyone talks (ramped over ~0.35s - real
    trailer pumping, not steps) and swells back between lines. `music_vol`
    overrides the branding bed level (trailers mix the score LOUD),
    `swell` grows the score from ~70% into full by that timestamp."""
    if base is not None:
        video_in = ["-i", base.name]
    else:
        colors = pkg.get("colors") or {}
        c0 = hex_to_ffmpeg(colors.get("from"), "0x151a30")
        c1 = hex_to_ffmpeg(colors.get("to"), "0x6a5ae0")
        video_in = ["-f", "lavfi", "-i",
                    f"gradients=s={WIDTH}x{HEIGHT}:c0={c0}:c1={c1}:speed=0.012:rate={FPS}"]

    inputs = [*video_in, "-i", "voice.mp3"]
    filters = ["[0:v]ass=subs.ass:fontsdir=.[v]", "[1:a]apad[va]"]
    mix = ["[va]"]
    if clip_audio > 0 and base is not None:
        filters.append(f"[0:a]volume={clip_audio}[ca]")
        mix.append("[ca]")
    music_files = list(Path(tmp).glob("music.*"))
    if has_music and music_files:
        inputs += ["-i", music_files[0].name]
        fade_start = max(0.0, total - 1.5)
        vol = music_vol if music_vol else branding_for(pkg)["music_volume"]
        swell_f = ""
        if swell:
            swell_f = (f"volume='min(1,0.7+0.3*t/{max(swell, 1.0):.2f})'"
                       ":eval=frame,")
        duck_f = ""
        if duck:
            # Each span contributes a trapezoid (0.35s attack/release);
            # max() folds them into one smooth gain curve.
            expr = "0"
            for s, e in duck[:60]:
                expr = (f"max({expr},min(1,min((t-{s - 0.35:.2f})/0.35,"
                        f"({e + 0.35:.2f}-t)/0.35)))")
            duck_f = f"volume='1-0.7*({expr})':eval=frame,"
        filters.append(f"[2:a]volume={vol},{swell_f}{duck_f}"
                       f"afade=t=out:st={fade_start:.2f}:d=1.5[m]")
        mix.append("[m]")
    # Beat-timed sound design (sfx.wav + its start offset, prepared by the
    # render loop when the category asks for it).
    sfx_file = Path(tmp) / "sfx.wav"
    if sfx_delay_ms is not None and sfx_file.exists():
        sfx_idx = 3 if (has_music and music_files) else 2
        inputs += ["-i", "sfx.wav"]
        filters.append(f"[{sfx_idx}:a]adelay={int(sfx_delay_ms)}:all=1[sfx]")
        mix.append("[sfx]")
    if len(mix) > 1:
        filters.append("".join(mix) + f"amix=inputs={len(mix)}:duration=first:normalize=0[a]")
    else:
        filters[1] = "[1:a]apad[a]"

    cmd = [ffmpeg, "-y", *inputs, "-filter_complex", ";".join(filters),
           "-map", "[v]", "-map", "[a]", "-t", f"{total + 0.3:.2f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out_path)]
    run(cmd, cwd=tmp)


# ---------------------------------------------------------------- post kit

# Per-platform anchor tags + how many total to suggest. Mirrors PLATFORMS in
# app.js. TikTok/YT lean on caption + title, so they stay tight; Reels leans on
# hashtags for discovery, so it gets a roomier cap.
PLATFORM_TAGS = {
    "TikTok":    {"format": "#fyp",    "community": "#storytime",  "cap": 5},
    "YT Shorts": {"format": "#shorts", "community": "#storytime",  "cap": 4},
    "Reels":     {"format": "#reels",  "community": "#didyouknow", "cap": 8},
}

# Topic ("niche") tags per scenario category - these steer the video toward the
# right feed. Keys mirror CATEGORIES in app.js.
CATEGORY_HASHTAGS = {
    "Speculative":         ["#thoughtexperiment", "#hypothetical"],
    "Science":             ["#science", "#sciencetok", "#space"],
    "History":             ["#history", "#historytok"],
    "Pop Culture":         ["#popculture", "#entertainment"],
    "Internet Mystery":    ["#internetmystery", "#unsolved", "#mystery"],
    "Alternate Reality":   ["#alternatehistory", "#multiverse"],
    "Unsettling Everyday": ["#creepy", "#unsettling", "#liminal"],
    "Scary/Weird":         ["#creepy", "#scary", "#creepytok"],
    "AI Remake":           ["#ai", "#aitrailer", "#aivideo", "#aimovie"],
    "Scary Story":         ["#horrortok", "#creepypasta", "#scary"],
    "True History":        ["#historytok", "#historyfacts", "#truestory"],
}


def _scenario_hashtags(pkg):
    """The package's own topic words as clean hashtags (may be empty)."""
    out = []
    for t in (pkg.get("tags") or []):
        slug = re.sub(r"[^a-z0-9]", "", str(t).lower())
        if slug:
            out.append("#" + slug)
    return out


def hashtags_for(platform, pkg):
    """A tiered tag set for one platform: broad + format + community anchors,
    then category-niche and scenario-specific topic tags, deduped and capped."""
    conf = PLATFORM_TAGS.get(platform, {"format": "", "community": "", "cap": 6})
    ordered = [branding_for(pkg)["anchor"], conf["format"], conf["community"]]
    ordered += CATEGORY_HASHTAGS.get(pkg.get("category", ""), [])
    ordered += _scenario_hashtags(pkg)
    seen, tags = set(), []
    for t in ordered:
        key = t.lower()
        if t and key not in seen:
            seen.add(key)
            tags.append(t)
    return " ".join(tags[:conf["cap"]])


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
    made_for = pkg.get("platform", "")
    cat = pkg.get("category", "")
    header = f"CROSS-POSTING - same video, hashtags tuned for {cat or 'this'} content:"
    lines.append(header)
    for name in PLATFORM_TAGS:
        mark = "  (this cut)" if name == made_for else ""
        lines.append(f"- {name}: {hashtags_for(name, pkg)}{mark}")
    if made_for in PLATFORM_TAGS:
        # Legacy per-platform package: its outro CTA was written for one platform.
        lines.append(f"Heads-up: the spoken outro was cut for {made_for} - "
                     "re-render with another platform selected if you want its call-to-action in the audio.")
    else:
        lines.append("The spoken outro is platform-neutral - the same audio works everywhere.")
    lines.append("")
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
    parser.add_argument("--trailer", action="store_true",
                        help="Movie-trailer treatment: an epic cinematic bed from music/trailer "
                             "(python get_music.py fetches the tracks) and the riser + impact on "
                             "the reveal beat for EVERY category. Pair with --mood trailer for "
                             "trailer-look visuals and trailer-speak rewrites on the Produce page.")
    parser.add_argument("--score", choices=sorted(TRAILER_SCORES), default=None,
                        help="Force the trailer score genre. Default: the package's "
                             "'score' field (the writer sets it), else inferred from "
                             "the story (title + premise + tags).")
    parser.add_argument("--trailer-bed", choices=["auto", "dread", "epic"], default="auto",
                        help="Soundtrack for --trailer: 'dread' = ONLY the synthesized AHS-style "
                             "unsettling bed, 'epic' = ONLY an orchestral track from music/trailer. "
                             "'auto' (default) layers score + dread bed for horror categories, "
                             "score alone otherwise. Music always ducks under character lines.")
    parser.add_argument("--ironic-music", nargs="?", const="tail", choices=["tail", "stop"],
                        default=None,
                        help="Sincerely cheerful music that contradicts the visuals and tape-stops "
                             "on the reveal beat. 'tail' (default) lets the song resume slowed and "
                             "quiet after the stop; 'stop' leaves silence. Uses music/ironic "
                             "(python get_music.py fetches the tracks).")
    parser.add_argument("--mood", default=None, choices=sorted(MOOD_LOOKS),
                        help="Fold a mood look into every generated visual's style suffix "
                             "(images, AI-video frames and motion). Omit = the classic look. "
                             "Caches are not forked - delete a scenario's cache entry to restyle it.")
    parser.add_argument("--ai-style", default=None, choices=sorted(AI_STYLES),
                        help="Look of generated AI visuals (default: the category's own style - "
                             "eerie for Scary Story, archival for True History, cinematic otherwise)")
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
    parser.add_argument("--infer-images", metavar="MODEL",
                        help="Generate a paid AI IMAGE per beat via tryinfer text-to-image (e.g. nano-banana, flux-2; "
                             "cheaper than --infer, uses --ai-style for the look)")
    parser.add_argument("--infer-images-cache", default="infer-images",
                        help="Cache folder for tryinfer-generated images (default: infer-images)")
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
    parser.add_argument("--prompt-sheet", action="store_true",
                        help="Write per-beat video prompts (for pasting into tryinfer Studio etc.) instead of rendering")
    parser.add_argument("--clip-audio", type=float, default=0.0, metavar="VOL",
                        help="Keep the clips' own sound (e.g. LTX ambience) mixed under the voice at this volume (try 0.25)")
    parser.add_argument("--no-people", action="store_true",
                        help="Don't add a person to visual prompts for shots that lack one (people are added by default)")
    parser.add_argument("--no-polish", action="store_true",
                        help="Skip the OpenAI prompt polish (it runs automatically when an OpenAI key is configured)")
    parser.add_argument("--no-sfx", action="store_true",
                        help="Skip the beat-timed sound design (Scary Story gets a riser + soft impact on the reveal beat by default)")
    parser.add_argument("--hook", type=int, default=1, choices=[1, 2, 3],
                        help="Which of the 3 hooks opens the video (default: 1)")
    parser.add_argument("--voice", help="Override edge-tts voice for all items")
    parser.add_argument("--rate", help="Override speech rate, e.g. +10%%")
    parser.add_argument("--pitch", help="Override speech pitch, e.g. -2Hz")
    parser.add_argument("--slots", help="Only render these queue slots, e.g. 1,3,4")
    args = parser.parse_args()

    global PEOPLE_BIAS, POLISH_PROMPTS
    if args.no_people:
        PEOPLE_BIAS = False
    if args.no_polish:
        POLISH_PROMPTS = False
    elif openai_key():
        print("Prompt polish ON - OpenAI rewrites each scenario's visual prompts once (cached).")

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

    if args.prompt_sheet:
        for slot, item, pkg in items:
            segments = narration_segments(pkg, hook_index)
            slug = f"{slot:02d}-{slugify(pkg.get('title', 'untitled'))}"
            lines = [
                f"VIDEO PROMPT SHEET - {pkg.get('title', 'untitled')}",
                "Paste each prompt into tryinfer Studio (or any AI video tool).",
                "Settings per clip: 9:16 vertical, 5s (or 10s), Seedance or your favorite model.",
                "",
            ]
            for i, seg in enumerate(segments):
                prompt = ai_prompt_for_segment(pkg, i, len(segments), VIDEO_MOTION_SUFFIX)
                lines += [f"=== Clip {i + 1:02d} of {len(segments)} ===", prompt, ""]
            lines += [
                "HOW TO ASSEMBLE:",
                "1. Generate + download each clip; name them 01.mp4, 02.mp4, ... in clip order.",
                "2. Empty pipeline/backgrounds/ and drop the clips in.",
                "3. Render (voice, captions, charts, music, cards are added automatically):",
                f"   python make_videos.py {args.queue} --slots {slot} --elevenlabs --charts",
                "4. For a different scenario, empty backgrounds/ first - clips map to beats in filename order.",
            ]
            sheet = out_dir / f"{slug}-prompts.txt"
            sheet.write_text("\n".join(lines), encoding="utf-8")
            print(f"[slot {slot}] prompt sheet -> {sheet}")
        sys.exit(0)

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
    if args.infer or args.infer_images:
        infer_key = infer_api_key()
        if not infer_key:
            sys.exit(
                "--infer / --infer-images need your tryinfer API key.\n"
                "  Set the TRYINFER_API_KEY environment variable, or save the key (one line)\n"
                "  in pipeline/tryinfer_key.txt. Then re-run.")
        billed = "one clip" if args.infer else "one image"
        print(f"NOTE: this run uses the PAID tryinfer API - {billed} is billed per beat.\n")

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
        print(f"Visuals: free AI images per beat (style: {args.ai_style or 'per-category'}, cache: {args.ai_cache})")
    else:
        print(f"Visuals: {len(visuals)} file(s) in '{args.backgrounds}'"
              + (" (one clip per beat)" if len(visuals) > 1 else " (single background)" if visuals else " (animated gradient)"))
    print()
    failures = 0

    for slot, item, pkg in items:
        title = pkg.get("title", "untitled")
        base_slug = f"{slot:02d}-{slugify(title)}"
        slug = versioned_slug(out_dir, base_slug)
        out_path = out_dir / f"{slug}.mp4"
        print(f"[slot {slot}] {title}")
        if slug != base_slug:
            print(f"  earlier render kept - this one saves as {out_path.name}")

        vconf = dict(VOICE_MAP.get(pkg.get("voice"), DEFAULT_VOICE))
        if args.trailer:
            # Trailer VO delivery: noticeably slower and a touch deeper - the
            # pauses the trailer-mood script writes (' - ', '...') get room to
            # land. Character dialogue keeps its own natural pace; explicit
            # --rate/--pitch below still win.
            vconf["rate"], vconf["pitch"] = "-15%", "-8Hz"
        if args.voice:
            vconf["voice"] = args.voice
        if args.rate:
            vconf["rate"] = args.rate
        if args.pitch:
            vconf["pitch"] = args.pitch

        # raw_segments may carry [Name] "line" dialogue markup; `segments` is
        # the SPOKEN form (tags stripped, quoted words kept) - it's what the
        # word timings, spans, captions, charts, and prompts all line up with.
        raw_segments = narration_segments(pkg, hook_index)
        segments = [strip_dialogue_markup(s) for s in raw_segments]
        # Clip-voiced beats (lipsync.json): the staged talking clip carries
        # the spoken line - the voice track holds silence there instead.
        clip_voiced = {}
        for idx1 in lipsync_map(args.backgrounds):
            si = idx1 - 1
            if (0 <= si < len(segments)
                    and _ref_choice(args.backgrounds, idx1) == "video"):
                v = _ref_video(args.backgrounds, idx1)
                if v:
                    clip_voiced[si] = v
        # Cast synthesis handles character voices, (silence) holds, and
        # clip-voiced beats - the plain path would read markers aloud.
        has_dialogue = (any(sp for s in raw_segments for sp, _ in split_dialogue(s))
                        or any(SILENCE_RE.match(s) for s in raw_segments)
                        or bool(clip_voiced))
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
                brand_font_path, _ = brand_font(pkg)
                if brand_font_path:
                    shutil.copy(brand_font_path, tmp / brand_font_path.name)

                cast = None
                # Trailer VO on ElevenLabs: lower stability = a hotter, more
                # dramatic read instead of the even narration default.
                el_settings = ({"stability": 0.35, "similarity_boost": 0.75}
                               if args.trailer else None)
                if args.elevenlabs:
                    el_voice_id, el_voice_name = pick_elevenlabs_voice(
                        pkg.get("voice", ""), args.el_voice, el_key)
                    if has_dialogue:
                        words, cast = synthesize_cast(
                            raw_segments, vconf, tmp / "voice.mp3", tmp, ffmpeg, ffprobe,
                            eleven={"key": el_key, "model": args.el_model,
                                    "narrator_id": el_voice_id,
                                    "voices": elevenlabs_voices(el_key),
                                    "settings": el_settings},
                            narrator_tempo=TRAILER_TEMPO if args.trailer else 1.0,
                            pad=0.7 if args.trailer else 0.15,
                            clip_voiced=clip_voiced, cast_info=pkg.get("cast"))
                    else:
                        words = synthesize_elevenlabs(text, el_voice_id, args.el_model,
                                                      tmp / "voice.mp3", el_key,
                                                      settings=el_settings)
                        if args.trailer:
                            # ElevenLabs has no rate knob - slow the whole VO
                            # (pitch preserved) and stretch the word timings.
                            slow = tmp / "voice-slow.mp3"
                            run([ffmpeg, "-y", "-i", str(tmp / "voice.mp3"),
                                 "-af", f"atempo={TRAILER_TEMPO}",
                                 "-c:a", "libmp3lame", "-q:a", "3", str(slow)])
                            (tmp / "voice.mp3").unlink()
                            slow.rename(tmp / "voice.mp3")
                            words = [(s / TRAILER_TEMPO, e / TRAILER_TEMPO, t)
                                     for s, e, t in words]
                    total = probe_duration(ffprobe, tmp / "voice.mp3")
                    print(f"  voice: ElevenLabs {el_voice_name} ({args.el_model}) - {total:.1f}s"
                          + (f" (trailer pace x{TRAILER_TEMPO})" if args.trailer else ""))
                else:
                    if has_dialogue:
                        words, cast = synthesize_cast(
                            raw_segments, vconf, tmp / "voice.mp3", tmp, ffmpeg, ffprobe,
                            pad=0.7 if args.trailer else 0.15,
                            clip_voiced=clip_voiced, cast_info=pkg.get("cast"))
                    else:
                        words = asyncio.run(synthesize(text, vconf, tmp / "voice.mp3"))
                    total = probe_duration(ffprobe, tmp / "voice.mp3")
                    print(f"  voice: {vconf['voice']} ({vconf['rate']}, {vconf['pitch']}) - {total:.1f}s")
                if cast:
                    print("  cast: " + ", ".join(f"{ch} -> {label}"
                                                 for ch, (label, _) in cast.items()))
                (tmp / "subs.ass").write_text(words_to_ass(words, pkg, total), encoding="utf-8")

                # Where the reveal lands (segments[-3] = the second-to-last
                # body beat): shared by the beat SFX and the ironic-music
                # tape-stop below.
                reveal_start = None
                if len(segments) >= 4 and total > 20:
                    t0 = segment_spans(segments, words, total)[len(segments) - 3][0]
                    if t0 > 6:
                        reveal_start = t0

                # Beat-timed sound design on the reveal's first word. Ironic
                # mode drops the riser - a swell would telegraph the dread the
                # cheerful song is busy denying - and keeps just the impact,
                # landing together with the music's tape-stop.
                sfx_delay_ms = None
                if reveal_start is not None and not args.no_sfx:
                    if args.ironic_music:
                        synth_reveal_sfx(tmp / "sfx.wav", riser=0.3)
                        sfx_delay_ms = int((reveal_start - 0.3) * 1000)
                        print(f"  sfx: soft impact on the reveal at {reveal_start:.1f}s")
                    elif branding_for(pkg).get("sfx") == "reveal" or args.trailer:
                        lead = min(3.0, reveal_start - 1.0)
                        synth_reveal_sfx(tmp / "sfx.wav", riser=lead)
                        sfx_delay_ms = int((reveal_start - lead) * 1000)
                        print(f"  sfx: sub-bass riser into the reveal at {reveal_start:.1f}s")

                item_visuals = visuals
                stock_authors = set()
                item_style = args.ai_style or branding_for(pkg)["style"]
                if args.mood:
                    print(f"  mood: {args.mood} - {MOOD_LOOKS[args.mood]}")
                if args.infer:
                    print(f"  generating AI video with {args.infer_model}...")
                    item_visuals = generate_infer_videos(pkg, segments, infer_key, args.infer_model,
                                                         args.infer_task, args.infer_duration, args.infer_cache,
                                                         ref_dir=args.backgrounds, ffmpeg=ffmpeg, mood=args.mood)
                elif args.infer_images:
                    print(f"  generating AI images with {args.infer_images}...")
                    item_visuals = generate_infer_images(pkg, len(segments), infer_key, args.infer_images,
                                                         item_style, args.infer_images_cache, mood=args.mood)
                elif args.stock:
                    print("  fetching Pexels stock footage...")
                    item_visuals = fetch_stock_visuals(pkg, segments, stock_key, args.stock_cache, stock_authors)
                elif args.ai_visuals:
                    print(f"  generating AI visuals ({item_style})...")
                    item_visuals = generate_ai_visuals(pkg, len(segments), item_style, args.ai_cache, mood=args.mood)

                # Per-beat reference overrides from the Produce page: a beat
                # whose radio says "video" plays that uploaded clip in EVERY
                # mode (in --infer the generation for it was already skipped
                # above); a beat whose radio says "image" shows the picture
                # itself with the Ken Burns move in every mode EXCEPT --infer,
                # where the clip is already animated FROM that image.
                over = {i: _ref_video(args.backgrounds, i + 1) for i in range(len(segments))
                        if _ref_choice(args.backgrounds, i + 1) == "video"}
                img_over = {} if args.infer else {
                    i: _ref_frame(args.backgrounds, i + 1) for i in range(len(segments))
                    if _ref_choice(args.backgrounds, i + 1) == "image"}
                over.update(img_over)   # disjoint: one radio choice per beat
                if over:
                    if item_visuals:
                        per_beat = [item_visuals[i % len(item_visuals)] for i in range(len(segments))]
                    else:
                        ordered = [over[i] for i in sorted(over)]
                        per_beat = [ordered[i % len(ordered)] for i in range(len(segments))]
                    for i, v in over.items():
                        per_beat[i] = v
                    item_visuals = per_beat
                    vids = len(over) - len(img_over)
                    notes = ([f"{vids} beat(s) play your uploaded video"] if vids else []) \
                        + ([f"{len(img_over)} beat(s) show your attached image"] if img_over else [])
                    print("  visuals: " + ", ".join(notes))

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

                # Per-beat audio: clip-voiced beats play their own sound (the
                # character speaking) at full volume; everything else follows
                # --clip-audio (0 = muted, the default).
                keep_audio = args.clip_audio > 0 or bool(clip_voiced)
                gains = None
                if clip_voiced:
                    gains = [1.0 if i in clip_voiced else args.clip_audio
                             for i in range(len(segments))]
                    print(f"  lipsync: {len(clip_voiced)} beat(s) speak from their clip")
                base = None
                if len(item_visuals) > 1:
                    spans = segment_spans(segments, words, total)
                    base = build_clip_base(ffmpeg, item_visuals, spans, tmp, charts=charts, font_ff=font_ff,
                                           keep_audio=keep_audio, ffprobe=ffprobe,
                                           audio_gains=gains)
                    print(f"  visuals: {len(spans)} beat clips from {len(item_visuals)} source file(s)"
                          + (f" (clip audio at {args.clip_audio})" if args.clip_audio > 0 else ""))
                elif len(item_visuals) == 1:
                    seg = tmp / "base.mp4"
                    render_segment_clip(ffmpeg, item_visuals[0], total + 0.4, seg,
                                        keep_audio=keep_audio, ffprobe=ffprobe)
                    base = seg
                    print(f"  visuals: single background ({item_visuals[0].name})")
                else:
                    print("  visuals: generated gradient")

                # Trailer soundtrack: a REAL score always (music/trailer -
                # orchestral by default, genre folders welcome); horror ALSO
                # layers the synthesized dread bed under it, still climaxing
                # on the reveal. --trailer-bed dread = bed only, epic = score
                # only.
                dread = args.trailer and args.trailer_bed != "epic" and (
                    args.trailer_bed == "dread"
                    or branding_for(pkg).get("sfx") == "reveal")
                score = None
                if args.trailer:
                    score = args.score or pkg.get("score") or infer_score(pkg)
                    if score not in TRAILER_SCORES:
                        score = infer_score(pkg)
                music = None
                premixed = False

                def normalize_score(src, dest):
                    # incompetech tracks span ~20 dB of loudness (epic battle
                    # vs sparse piano) - normalize every trailer score to the
                    # same perceived level (EBU R128) so the genre choice
                    # never decides whether the music is audible.
                    run([ffmpeg, "-y", "-i", str(src), "-t", f"{total + 1:.2f}",
                         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100",
                         "-c:a", "pcm_s16le", str(dest)])

                if dread:
                    synth_dread_bed(tmp / "dread.wav", total + 1.0, climax=reveal_start)
                    peak_at = reveal_start if reveal_start else 0.85 * (total + 1.0)
                    music = None if args.trailer_bed == "dread" else \
                        pick_music(pkg, args.music, override="trailer", score=score)
                    if music:
                        # The strings LEAD, the dread bed supports underneath
                        # (its own climax still lands - it just doesn't fight
                        # the melody for the same space).
                        normalize_score(music, tmp / "score.wav")
                        st = "aformat=sample_fmts=fltp:channel_layouts=stereo"
                        run([ffmpeg, "-y", "-i", str(tmp / "score.wav"),
                             "-i", str(tmp / "dread.wav"),
                             "-filter_complex",
                             f"[0:a]{st},volume=1.0[m];[1:a]aresample=44100,{st},volume=0.6[d];"
                             "[m][d]amix=inputs=2:duration=longest:normalize=0,"
                             "alimiter=limit=0.95[out]",
                             "-map", "[out]", "-c:a", "pcm_s16le", str(tmp / "music.wav")])
                        (tmp / "score.wav").unlink()
                        premixed = True
                        print(f"  music: {music.parent.name}/{music.name}"
                              f" [{score} score, loudness-normalized]"
                              f" + dread bed (climax at {peak_at:.1f}s)")
                    else:
                        (tmp / "dread.wav").rename(tmp / "music.wav")
                        print(f"  music: synthesized dread bed, building to a climax at {peak_at:.1f}s"
                              " (heartbeat pulse, detuned drone, metallic shrieks)")
                else:
                    music = pick_music(pkg, args.music,
                                       override=("ironic" if args.ironic_music
                                                 else "trailer" if args.trailer else None),
                                       score=score)
                if music and not premixed and args.trailer:
                    normalize_score(music, tmp / "music.wav")
                    premixed = True
                    print(f"  music: {music.parent.name}/{music.name}"
                          f" [{score} score, loudness-normalized]")
                if music and not premixed:
                    shutil.copy(music, tmp / ("music" + music.suffix))
                    print(f"  music: {music.parent.name}/{music.name}")
                    if args.ironic_music and reveal_start is not None:
                        ironic_music_treatment(ffmpeg, tmp / ("music" + music.suffix),
                                               tmp / "music-ironic.wav", reveal_start,
                                               args.ironic_music)
                        (tmp / ("music" + music.suffix)).unlink()
                        (tmp / "music-ironic.wav").rename(tmp / "music.wav")
                        print(f"  music: sincerely cheerful until the reveal at {reveal_start:.1f}s,"
                              f" then tape-stop"
                              + (" + warped tail" if args.ironic_music == "tail" else " to silence"))

                # Clip-voiced gains are baked per beat in the base track, so
                # the final mix takes it at unity instead of --clip-audio.
                mix_gain = (1.0 if clip_voiced else args.clip_audio)
                duck = speech_intervals(words) if args.trailer and words else None
                if duck:
                    print(f"  music: ducking under {len(duck)} spoken passages"
                          " (smooth trailer pumping)")
                # Trailers mix the score at soundtrack level, not bed level -
                # loud between lines (which also buries any synthetic edge in
                # the voices), dipping under speech, growing into the reveal.
                final_render(ffmpeg, base, pkg, total, bool(music) or dread, out_path.resolve(), tmp,
                             clip_audio=mix_gain if base is not None else 0.0,
                             sfx_delay_ms=sfx_delay_ms, duck=duck,
                             music_vol=0.6 if args.trailer else None,
                             swell=((reveal_start or 0.85 * total)
                                    if args.trailer else None))

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
            # Sidecar metadata so the dashboard's Results page can roll up
            # performance by category/runtime/voice - and by the render's
            # recipe (format/mood/visuals), so formats can compete on numbers.
            (out_dir / f"{slug}-meta.json").write_text(json.dumps({
                "title": pkg.get("title", ""), "category": pkg.get("category", ""),
                "scenarioId": pkg.get("scenarioId", ""), "runtime": pkg.get("runtime"),
                "voice": pkg.get("voice", ""), "hook": hook_index + 1,
                "format": ("trailer" if args.trailer
                           else "ironic" if args.ironic_music else "classic"),
                "mood": args.mood or "",
                "score": score if args.trailer else "",
                "visuals": ("ai-video" if args.infer
                            else "paid-images" if args.infer_images
                            else "stock" if args.stock
                            else "free-images" if args.ai_visuals else "clips"),
                "renderedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }, indent=2), encoding="utf-8")
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
