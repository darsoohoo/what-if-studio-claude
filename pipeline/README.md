# What If Studio — Video Pipeline (optional companion tool)

Turns queue exports from the app into **finished vertical videos**: AI voiceover, background visuals, and word-synced captions burned in. You review each video and post it yourself.

The app never requires this tool — it stays a plain static page. This is the "hands-off production" add-on.

## One-time setup (Windows)

1. **Python 3.9+** — check with `python --version` (install from python.org or `winget install Python.Python.3.12`)
2. **ffmpeg** — `winget install Gyan.FFmpeg` (the script auto-detects the winget install; no PATH fiddling needed)
3. **edge-tts** — from this folder run:
   ```
   python -m pip install --user -r requirements.txt
   ```
4. *(Optional but recommended)* Drop a few copyright-free vertical background videos into `backgrounds/` (see the README in that folder). Without them, the pipeline generates an animated gradient in each scenario's brand colors — clean, but real footage retains viewers better.
5. *(Optional)* Drop royalty-free music into `music/` — it gets mixed in quietly at 12% volume.

## Daily workflow

1. In the app: build your queue (generate packages, save to slots), then click **Export queue (.json) for video pipeline**.
2. Move the downloaded `whatifstudio-queue.json` into this folder (or point the script at your Downloads folder).
3. Run:
   ```
   python make_videos.py whatifstudio-queue.json
   ```
4. Finished videos land in `output/` as `01-<title>.mp4`, each with a matching `01-<title>-post.txt` containing caption options, hashtags, title ideas, and your queue notes.
5. Watch each video, pick a caption from the post kit, and upload.

## Options

```
python make_videos.py queue.json --hook 2            # open with hook #2 instead of #1
python make_videos.py queue.json --slots 1,3         # render only those queue slots
python make_videos.py queue.json --voice en-US-AriaNeural
python make_videos.py queue.json --rate +15% --pitch +2Hz
python make_videos.py package.json                   # single "Export .json" package works too
```

The app's voice styles map to neural voices automatically: Calm Narrator → Christopher, High-Energy Storyteller → Guy (faster), Deadpan Documentarian → Eric (slower, flatter). List every available voice with `python -m edge_tts --list-voices`.

## Good to know

- **Internet required** for voice generation (the neural voices are a Microsoft service; no account or API key).
- **Captions are word-synced** to the actual speech — the pipeline reads word timings from the TTS engine, so subtitles land exactly when words are spoken (better than the app's estimated `.srt`, which remains useful for manual editing workflows).
- **Video length** is set by real speech duration, not the app's runtime setting — a "60s" package typically renders 45–75s depending on voice and rate.
- **Disclosure:** TikTok and YouTube require labeling realistic AI-generated content. Tick the AI-content disclosure when posting — the post kit reminds you every time.
- **Monetization reality check:** fully automated TTS-over-gradient uploads are exactly what YouTube's "mass-produced or repetitious" review flags. Watch every video before posting, vary hooks (`--hook`), add your own edits or b-roll when you can, and treat this output as a strong first draft, not a finished channel.
- **Nothing is posted automatically.** That's deliberate: platform rules, and you staying the editor of record.
