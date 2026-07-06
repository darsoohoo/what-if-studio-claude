# What If Studio — Video Pipeline (optional companion tool)

Turns queue exports from the app into **finished vertical videos**: AI voiceover, per-beat visuals, and modern word-by-word "pop" captions burned in. You review each video and post it yourself.

**Captions** are Poppins ExtraBold, all-caps, centered, one short phrase at a time, with the currently-spoken word popping in yellow (the TikTok/CapCut look). Timing comes from the TTS engine's own word boundaries, so highlights land exactly on the spoken word.

**Visuals**: put clips/images in `backgrounds/`. With **several files, each script beat gets its own clip in order** — perfect for "one example per beat" videos. With one file it's used throughout; with none, an animated gradient in the scenario's colors is generated.

**Free AI visuals** (`--ai-visuals`): generates one custom image per beat from the scenario's own shot list, using Pollinations (free, no account, no key — internet required). Images are cached in `ai-visuals/` per scenario+style, so re-renders are instant. Pick a look with `--ai-style`:

```
python make_videos.py queue.json --ai-visuals                        # cinematic (default)
python make_videos.py queue.json --ai-visuals --ai-style dark        # eerie/horror topics
python make_videos.py queue.json --ai-visuals --ai-style 3d          # pixar-ish characters
python make_videos.py queue.json --ai-visuals --ai-style infographic # flat corporate vector look
```

To regenerate a scenario's images (new random look), delete its folder in `ai-visuals/`. AI images make the whole video AI-generated content — the disclosure reminder in each post kit covers this.

**Real stock footage** (`--stock`): uses actual vertical video clips from Pexels — real motion instead of AI stills — one clip per beat, keyword-matched from each beat's nouns. Free, but needs a Pexels API key:

1. Sign up (free) at https://www.pexels.com/api/ and copy your key.
2. Set the `PEXELS_API_KEY` environment variable, **or** save the key (one line) in `pipeline/pexels_key.txt` (git-ignored).
3. Run:
   ```
   python make_videos.py queue.json --stock --charts
   ```

Clips cache in `stock/` per scenario. Pexels clips are generic (topical, not scene-specific), so they read as real b-roll rather than exact illustrations. Attribution isn't required but is appreciated — the post kit lists the videographers and a Pexels credit line for you to paste.

**Paid AI video** (`--infer`): generates a bespoke motion clip per beat via [tryinfer](https://tryinfer.com) (Seedance, etc.). Each beat's clip is an `image-to-video` job that animates a free Pollinations first frame — so every clip shares one style anchor and the sequence feels like one production once the pipeline adds voice, captions, music, and crossfades.

1. Put your tryinfer key in `TRYINFER_API_KEY` or `pipeline/tryinfer_key.txt` (git-ignored).
2. **Confirm it works cheaply first** — one clip:
   ```
   python infer_probe.py            # submits ONE 5s clip, prints the result
   ```
3. Then render:
   ```
   python make_videos.py queue.json --infer --charts
   python make_videos.py queue.json --infer --infer-model happyhorse --infer-duration 10
   ```

**This is a paid API — real, verified pricing:** seedance-2.0-pro bills **$0.13/second ($0.65 per 5s clip)**, so a 7-beat video costs ≈ **$4.55** in clips (double for 10s clips). The renderer prints each clip's price and the total spend per run. Clips cache in `infer-videos/` per scenario+model, so re-renders don't re-bill. If the provider content-flags a first-frame image, that beat automatically retries as text-to-video. `--infer` makes the whole video AI-generated — keep the AI-content disclosure on when posting.

Given the cost, a sensible split: `--infer` for hero videos you expect to perform, `--ai-visuals` (free) or `--stock` (free) for daily volume.

**Animated charts** (`--charts`): beats whose narration contains a headline number get an animated graphic overlaid — a counter that ticks up ("8 → BILLION", "$50 MILLION", "30 DAYS") or, for percentages, a number plus a filling bar ("80 PERCENT"). Detection is conservative: one graphic per beat, only clear numbers, and it skips the hook and outro (owned by the title/CTA cards) and bare years. Needs per-beat visuals, so pair it with `--ai-visuals` or a multi-file `backgrounds/` folder:

```
python make_videos.py queue.json --ai-visuals --charts
```

The app never requires this tool — it stays a plain static page. This is the "hands-off production" add-on.

## One-time setup (Windows)

1. **Python 3.9+** — check with `python --version` (install from python.org or `winget install Python.Python.3.12`)
2. **ffmpeg** — `winget install Gyan.FFmpeg` (the script auto-detects the winget install; no PATH fiddling needed)
3. **edge-tts** — from this folder run:
   ```
   python -m pip install --user -r requirements.txt
   ```
4. *(Optional but recommended)* Drop a few copyright-free vertical background videos into `backgrounds/` (see the README in that folder). Without them, the pipeline generates an animated gradient in each scenario's brand colors — clean, but real footage retains viewers better.
5. *(Recommended)* Run `python get_music.py` once — it downloads a curated, properly-licensed music set into mood folders. Each video then gets a background bed matched to its scenario's mood (eerie / tense / wonder / upbeat), faded out at the end, with the required credit line added to the post kit automatically. See `music/README.md`.

## Review dashboard

Double-click **`review.bat`** to open a local dashboard (127.0.0.1 only) of every rendered video: watch them, drag your posting order (saved), write notes per video (autosaved), read each post kit, and **Remove** videos you don't want — removed files move to `output/trash`, never permanently deleted. Notes and order live in `review-notes.json`.

The dashboard also powers the app's **"✨ Write it for me"** button (in the Create-your-own-scenario form): it fetches a free AI draft of the premise/beats/tags server-side (the free service blocks direct browser calls). No key needed. The free tier handles **one request at a time per connection** — if you see "hiccuped", wait a minute and click again.

## Daily workflow (zero-click)

1. Double-click **`start-watcher.bat`** once when you sit down to create (it quietly watches your Downloads folder until you log off; nothing is installed).
2. In the app: build your queue, then click **Export queue (.json) for video pipeline**.
3. That's it. The watcher picks the export up from Downloads, renders every package with free AI visuals, and pops the `output/` folder open when done. Progress is logged to `watcher.log`.
4. Watch each video, copy a caption from its `-post.txt` post kit, and upload.

Manual alternatives: double-click **`run-queue.bat`** after each export, or run it yourself:

```
python make_videos.py whatifstudio-queue.json --ai-visuals
```

Finished videos land in `output/` as `01-<title>.mp4`, each with a matching `01-<title>-post.txt` (caption options, hashtags, title ideas, queue notes) and a `01-<title>-thumb.jpg` **cover image** — the title-card text over the opening visual, no captions. Upload it as your video's thumbnail so the platform doesn't pick a random frame.

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
- **Captions are word-synced** to the actual speech — the pipeline reads word timings from the TTS engine, so highlights land exactly when words are spoken (better than the app's estimated `.srt`, which remains useful for manual editing workflows).
- **Per-beat visuals** cycle through the `backgrounds/` folder in order. Beat count is hook + script beats + outro (7 for a 5-beat package), so ~7 clips gives every beat a distinct visual.
- **Video length** is set by real speech duration, not the app's runtime setting — a "60s" package typically renders 45–75s depending on voice and rate.
- **Disclosure:** TikTok and YouTube require labeling realistic AI-generated content. Tick the AI-content disclosure when posting — the post kit reminds you every time.
- **Monetization reality check:** fully automated TTS-over-gradient uploads are exactly what YouTube's "mass-produced or repetitious" review flags. Watch every video before posting, vary hooks (`--hook`), add your own edits or b-roll when you can, and treat this output as a strong first draft, not a finished channel.
- **Nothing is posted automatically.** That's deliberate: platform rules, and you staying the editor of record.
