# What If Studio

A local, static content engine for making short-form "What if?" videos — for TikTok, YouTube Shorts, or Reels — fast and repeatably.

Pick a scenario, generate a complete production package (hooks, script beats, shot list, captions, thumbnail text, and timed `.srt` subtitles), and queue up a week of content. Everything runs in your browser from a local file.

## Quick start

1. Download or clone this repository.
2. Double-click `index.html`. That's it — no install, no server, no account, no internet.

## What it does

- **Scenario Library** — 24 starter scenarios across 8 categories (Speculative, Science, History, Pop Culture, Internet Mystery, Alternate Reality, Unsettling Everyday, Scary/Weird), searchable and filterable. Each one is a complete content package, not just an idea.
- **Package Generator** — choose a platform (TikTok / YT Shorts / Reels), runtime (30s / 60s / 3 min), and voice style (Calm / High-Energy / Deadpan). The package adapts: beat count, pacing notes, outro, caption hashtags, and subtitle timing all follow your settings.
- **Exports** — copy any section, copy the full package, download it as `.txt`, or download timed subtitles as `.srt` sized to your chosen runtime.
- **Content Queue** — 7 slots to plan a week. Each slot tracks a saved package, a production status (Planned → Scripted → Recorded → Edited → Posted), and free-form notes. Persists across reloads via local storage.
- **New Scenario Seed** — one button that rotates fresh "what if" prompts through every category, so the idea well doesn't run dry after the starter set.

## A suggested daily workflow

1. Open `index.html`.
2. Pick a scenario (or hit **New Scenario Seed** for a fresh angle).
3. Set platform, runtime, and voice → **Generate Package**.
4. Read the beats aloud once, then record in your own words.
5. Export the `.srt` for captions, copy a caption option for the post.
6. Save the package to a queue slot and update its status as you go.

## Video pipeline (optional companion tool)

The app stays a pure static page — but if you want finished, ready-to-post videos, the optional [pipeline](pipeline/README.md) turns queue exports into complete vertical `.mp4`s: AI voiceover (free Microsoft neural voices), background visuals (your stock footage, or auto-generated gradients in each scenario's colors), and word-synced captions burned in. Each video ships with a "post kit" text file holding captions, hashtags, and title ideas.

Workflow: build your queue in the app → **Export queue (.json)** → `python make_videos.py whatifstudio-queue.json` → review → post. Nothing is uploaded automatically, and every post kit reminds you to enable the platform's AI-content disclosure. Setup instructions are in [pipeline/README.md](pipeline/README.md).

## Storage & recovery

- Your queue, statuses, notes, and seed rotation are saved in **your browser's local storage on this device**. Nothing is sent anywhere.
- Some browsers restrict local storage for pages opened directly from `file://`. When that happens the app switches to an in-memory fallback and the header badge reads **"Memory only — export to keep work"** — everything still works, but the queue resets when the tab closes. Use the export buttons to keep anything important.
- **Reset all local data** (header) clears the queue, notes, and seed rotation after a confirmation. Individual slots have their own **Clear** button. Exported files are never affected.

## Limitations (on purpose)

- No server, backend, login, API keys, npm dependencies, frameworks, tracking, or remote content. The whole app is `index.html` + `styles.css` + `app.js`.
- No automated publishing, bots, or engagement automation — you record and post your own videos, under your platforms' rules.
- No promises about virality, growth, or monetization. The tool makes production fast and consistent; results depend on you and your audience.
- All scenarios are speculative fiction and thought experiments, written with safety framing notes so speculation reads as speculation.

## Development

```
node --check app.js   # syntax check
git diff --check      # whitespace check
```

Scenario data lives in `app.js` in `scenarioBank`. Each scenario has: `id`, `category`, `title`, `image`, `premise`, `tags`, `safety`, `hooks`, `beats`, `shotList`, `captions`, `thumbnails`.

Docs live in `docs/`:

- [Content quality rubric](docs/content-quality-rubric.md)
- [QA checklist](docs/qa-checklist.md)
