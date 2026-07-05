# What If Studio — v1.0-beta

Local Beta release. A static, offline app for planning short-form "What if?" videos, plus an optional companion pipeline that renders finished, ready-to-post vertical videos.

## What's in it

**The app** (`index.html` + `styles.css` + `app.js` — opens by double-click, no install):

- Scenario library: 27 starter scenarios across 8 categories, searchable and filterable
- Create-your-own scenario builder: enter a title, premise, and a few beats; the app scaffolds a full package
- Package generator: platform (TikTok / Shorts / Reels), runtime (30s / 60s / 3 min), and voice style all propagate into beats, pacing, hashtags, outro, and subtitle timing
- Exports: copy any section, full package `.txt`, timed `.srt`, and `.json` for the pipeline
- 7-slot content queue with production status and tracker notes, persisted in local storage
- New Scenario Seed rotation across every category
- Accessible: keyboard-only workflow, visible focus, `prefers-reduced-motion` support, WCAG-AA contrast; responsive at 1366 / 820 / 390

**The pipeline** (`pipeline/` — optional, needs Python + ffmpeg):

- AI voiceover via free Microsoft neural voices (edge-tts)
- Modern word-by-word "pop" captions (Poppins ExtraBold), synced to the speech
- Free per-beat AI visuals (Pollinations — no account, no key), 4 style presets
- Production polish: title card, alternating camera motion, crossfades, closing CTA card
- Mood-matched, properly-licensed music beds with automatic credit lines
- Animated data charts: counters and bars on beats with a headline number
- Zero-click workflow: a session watcher renders automatically when you export a queue

## How to get it

- **Just the app:** download the release ZIP, unzip, and double-click `index.html`.
- **App + pipeline:** `git clone` the repo, then follow `pipeline/README.md` for the one-time setup.

Build the ZIP yourself anytime with `scripts/build-release.ps1` (packages exactly the committed files).

## Limitations (by design)

- The app is 100% local: no server, login, API keys, tracking, or remote content.
- Nothing is auto-posted. You review and upload every video yourself, under your platforms' rules.
- No promises about virality, growth, or monetization — the tools make production fast and consistent; results are up to you and your audience.
- AI-generated voice/visuals require the platform's AI-content disclosure at upload (each post kit reminds you).

## Credits

- Caption font: Poppins (SIL Open Font License 1.1)
- Music: Kevin MacLeod / incompetech.com (Creative Commons BY 4.0)
- Voice: Microsoft neural voices via edge-tts · Images: Pollinations · Rendering: ffmpeg
