# Music

Background beds mixed under the voiceover at 12% volume with an end fade-out.

**Quick setup:** from the `pipeline` folder run:

```
python get_music.py
```

That downloads a curated set of Kevin MacLeod (incompetech.com) tracks into mood
folders — `eerie/`, `tense/`, `wonder/`, `upbeat/`, `period/`, `ironic/`,
`trailer/` — and writes `credits.json`. The pipeline picks a track whose mood
matches the scenario's category (Scary/Weird → eerie, Internet Mystery &
Unsettling Everyday → tense, Pop Culture → upbeat, everything else → wonder)
and adds the required Creative Commons credit line to that video's post kit
automatically — just paste it into the video description when posting.

**Trailer scores** (`--trailer` renders) come in four genres the writer picks
to fit the story: **action**, **dark**, **tragedy**, **wonder**. The stock
tracks live in `trailer/` (and `wonder/`); every score is loudness-normalized
at render time, so quiet chamber pieces and epic battle tracks land at the
same level.

**Adding your own trailer scores:** drop files into the genre subfolders —
`trailer/action/`, `trailer/dark/`, `trailer/tragedy/`, `trailer/wonder/` —
and the picker treats them exactly like the stock tracks. Tracks from
YouTube's **Audio Library** (studio.youtube.com → Audio Library) are safe to
use: "no attribution required" tracks need nothing; "attribution required"
tracks need a credit line — add one to `credits.json` keyed by filename, e.g.
`"My Track.mp3": "Song by Artist, YouTube Audio Library"`, and the post kit
will carry it automatically. (Re-running `get_music.py` keeps your custom
entries.) Do NOT rip audio out of regular YouTube videos — being downloadable
isn't a license, and Content ID will flag it.

**Adding your own beds:** drop files into a mood folder (or loose in this
folder as a fallback pool). Instrumental, low-intensity tracks work best. If a
track isn't in `credits.json`, no credit line is added — only do that with
music that doesn't require attribution (check the license).

Supported: `.mp3 .m4a .wav .ogg .flac`
