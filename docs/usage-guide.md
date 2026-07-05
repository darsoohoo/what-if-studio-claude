# What If Studio — Usage Guide

A one-page walkthrough, from opening the app to posting a finished video.

## 1. Open the app

Double-click `index.html`. It opens in your browser and runs entirely offline — no install, no account. The header badge reads **"Saving locally on this device"** when your work is being saved.

Layout, left to right:
- **Scenario Library** — 27 ideas (plus any you create). Search or filter by category, then click a card.
- **Workspace** — pick platform, runtime, and voice, then **Generate Package** to see hooks, script beats, shot list, captions, and thumbnail text.
- **Content Queue** — 7 slots to plan a week, each with a status (Planned → Posted) and notes.

## 2. Make a package

1. Click a scenario (or **New Scenario Seed** for a fresh prompt, or **+ Create your own scenario** to write one).
2. Set platform / runtime / voice.
3. **Generate Package** → review the tabs.
4. Pick a slot and **Save to slot**. Repeat for as many videos as you want.

## 3. Turn the queue into videos (optional pipeline)

One-time setup (see `pipeline/README.md`): install Python + ffmpeg, run `python -m pip install --user -r pipeline/requirements.txt`, then `python get_music.py` for music.

Each session:
1. Double-click `pipeline/start-watcher.bat` once.
2. In the app, click **Export queue (.json) for video pipeline**.
3. Do nothing — the watcher renders every package (AI voice + visuals + captions + music) and opens the `pipeline/output` folder when done. A notification tells you it's working.

Prefer manual? Double-click `pipeline/run-queue.bat`, or run:

```
python pipeline/make_videos.py whatifstudio-queue.json --ai-visuals --charts
```

## 4. Post

For each video in `pipeline/output/`:
1. **Watch it once** — you're the editor of record.
2. Open the matching `-post.txt`: copy a caption, hashtags, and (if present) the required music credit.
3. Upload to TikTok / YouTube, paste the caption, and **turn on the AI-generated content disclosure**.

## Tips

- **Fresh visuals:** delete a scenario's folder in `pipeline/ai-visuals/` to regenerate its images.
- **Different look:** add `--ai-style dark` (eerie), `3d` (characters), or `infographic` to the render command.
- **Different opener:** `--hook 2` uses the second hook option.
- **Keep your work:** the queue lives in your browser on this device. If the badge says **"Memory only"**, your browser is blocking local storage for `file://` pages — export anything you want to keep.
- **Consistency beats everything.** A saved week of packages plus the watcher is built so posting daily is realistic.
