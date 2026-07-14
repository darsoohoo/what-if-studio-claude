#!/usr/bin/env python3
"""
What If Studio - music bed setup.

Downloads a small curated set of background tracks by Kevin MacLeod
(incompetech.com) into mood folders under music/, and writes the license
credits the post kits will include automatically.

License: Creative Commons: By Attribution 4.0
(https://creativecommons.org/licenses/by/4.0/) - free for commercial use
as long as the credit line is included in the video description. The
pipeline appends the exact credit line to each video's post kit, so
posting stays copy-paste simple.

Run once:  python get_music.py
Re-running skips files that already exist.
"""

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

MUSIC_DIR = Path(__file__).resolve().parent / "music"
BASE = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/"

# mood -> track titles (exact incompetech filenames, minus .mp3)
TRACKS = {
    "eerie": [
        "Ossuary 5 - Rest",
        "Ghost Story",
        "Night Vigil",
        # Creepy soundscapes: drones, music boxes, dark choirs - beds that
        # sit under quiet-horror narration without fighting it.
        "The House of Leaves",
        "Long Note Two",
        "Come Play with Me",
        "Gathering Darkness",
        "Penumbra",
    ],
    "tense": [
        "Lightless Dawn",
        "Hidden Agenda",
        "Static Motion",
    ],
    "wonder": [
        "Frozen Star",
        "Floating Cities",
    ],
    "upbeat": [
        "Carefree",
        "Wallpaper",
        "Monkeys Spinning Monkeys",
    ],
    # True History: period instruments for the documentary feel.
    "period": [
        "Suonatore di Liuto",
        "Teller of the Tales",
        "Lord of the Land",
    ],
    # Ironic mode (--ironic-music): sincerely cheerful beds meant to
    # CONTRADICT scary visuals - vintage swing, naive sweetness, elevator
    # muzak. The render keeps them cheerful until the reveal, then tape-stops.
    "ironic": [
        "Hep Cats",                   # 1950s-style swing
        "Fig Leaf Rag",               # jaunty ragtime
        "Wholesome",                  # naive, almost children's-music sweet
        "Sweeter Vermouth",           # gentle romantic lilt
        "Airport Lounge",             # cheesy easy-listening
        "Local Forecast - Elevator",  # corporate elevator muzak
    ],
}

CREDIT_TEMPLATE = ('"{title}" Kevin MacLeod (incompetech.com). '
                   "Licensed under Creative Commons: By Attribution 4.0. "
                   "https://creativecommons.org/licenses/by/4.0/")


def fetch(title, dest):
    url = BASE + urllib.parse.quote(title + ".mp3")
    req = urllib.request.Request(url, headers={"User-Agent": "WhatIfStudio-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
        out.write(resp.read())
    head = dest.read_bytes()[:3]
    if dest.stat().st_size < 200_000 or head not in (b"ID3", b"\xff\xfb", b"\xff\xf3"):
        dest.unlink(missing_ok=True)
        raise RuntimeError("response does not look like an mp3")


def main():
    credits = {}
    credits_path = MUSIC_DIR / "credits.json"
    if credits_path.exists():
        credits = json.loads(credits_path.read_text(encoding="utf-8"))

    ok, failed = 0, 0
    for mood, titles in TRACKS.items():
        folder = MUSIC_DIR / mood
        folder.mkdir(parents=True, exist_ok=True)
        for title in titles:
            safe = re.sub(r'[\\/:*?"<>|]', "-", title)
            dest = folder / f"{safe}.mp3"
            if dest.exists():
                print(f"  [skip] {mood}/{dest.name} (already downloaded)")
                credits[dest.name] = CREDIT_TEMPLATE.format(title=title)
                ok += 1
                continue
            try:
                fetch(title, dest)
                credits[dest.name] = CREDIT_TEMPLATE.format(title=title)
                size_mb = dest.stat().st_size / 1e6
                print(f"  [ok]   {mood}/{dest.name} ({size_mb:.1f} MB)")
                ok += 1
            except Exception as exc:
                print(f"  [fail] {mood}/{title}: {exc}")
                failed += 1

    credits_path.write_text(json.dumps(credits, indent=2), encoding="utf-8")
    (MUSIC_DIR / "CREDITS.md").write_text(
        "# Music credits\n\n"
        "All tracks by Kevin MacLeod (incompetech.com), Creative Commons: By Attribution 4.0.\n"
        "The credit line for the track used in each video is added to that video's post kit -\n"
        "paste it into the video description when you post.\n\n"
        + "\n".join(f"- {line}" for line in sorted(set(credits.values())))
        + "\n",
        encoding="utf-8",
    )
    print(f"\nDone: {ok} track(s) ready, {failed} failed. Credits written to music/credits.json")
    sys.exit(1 if (failed and not ok) else 0)


if __name__ == "__main__":
    main()
