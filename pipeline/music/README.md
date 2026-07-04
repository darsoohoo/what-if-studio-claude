# Music

Background beds mixed under the voiceover at 12% volume with an end fade-out.

**Quick setup:** from the `pipeline` folder run:

```
python get_music.py
```

That downloads a curated set of Kevin MacLeod (incompetech.com) tracks into mood
folders — `eerie/`, `tense/`, `wonder/`, `upbeat/` — and writes `credits.json`.
The pipeline picks a track whose mood matches the scenario's category
(Scary/Weird → eerie, Internet Mystery & Unsettling Everyday → tense,
Pop Culture → upbeat, everything else → wonder) and adds the required
Creative Commons credit line to that video's post kit automatically —
just paste it into the video description when posting.

**Adding your own:** drop files into a mood folder (or loose in this folder as a
fallback pool). Instrumental, low-intensity tracks work best. If a track isn't in
`credits.json`, no credit line is added — only do that with music that doesn't
require attribution (check the license).

Supported: `.mp3 .m4a .wav .ogg .flac`
