# What If Studio

A two-part product for making short-form "What if?" videos (TikTok/YouTube Shorts):

1. **The app** — `index.html` + `app.js` + `assistant.js` + `styles.css` (+ `help.html`). Static HTML/CSS/vanilla JS only; must run from `file://`; **no server, login, npm deps, tracking, remote content, or automated posting** — these are hard product constraints, do not violate them. Scenario library (27+), builder with AI draft, one-click "Generate + Export for render" (downloads a one-item queue .json the watcher picks up; packages are platform-neutral — hashtags come from the post kit). `assistant.js` is the studio assistant chat, shared by every page (dashboard pages load it at `/assistant.js`): offline commands + FAQ always; page-specific powers come from `window.assistantHost` (set by `app.js` on the Studio page); smart answers via the dashboard's `/api/chat` when it's running.
2. **The pipeline** — `pipeline/` (Python stdlib + ffmpeg + edge-tts, explicitly outside the app's constraints). `make_videos.py` renders queue exports into 1080×1920 videos: TTS voiceover, word-synced captions, per-beat visuals, music, thumbnails, post kits. `review.py` is a local-only dashboard (127.0.0.1:8765) serving the Videos/Produce/help pages plus `/api/draft` ("Write it for me") and `/api/chat` (the assistant's smart tier) for the app. Start everything with `Start-What-If-Studio.bat`.

## Commands

- Render: `python pipeline/make_videos.py <queue.json>` — flags: `--ai-visuals [style]`, `--charts`, `--elevenlabs`, `--infer` (paid AI video), `--stock` (Pexels), `--prompt-sheet`, `--clip-audio VOL`, `--no-people`, `--no-polish`, `--no-sfx`, `--slots N`
- Dashboard: `pipeline/review.bat` (or the root .bat) → http://127.0.0.1:8765
- Watcher (auto-render on queue export to Downloads): `pipeline/start-watcher.bat`

## API keys (all optional, all gitignored, one line per file)

`pipeline/openai_key.txt` (AI writer + prompt polish, auto-on when present), `pipeline/elevenlabs_key.txt` (premium voice; style map Calm→Adam, High-Energy→Callum, Deadpan→George), `pipeline/tryinfer_key.txt` (paid AI video), `pipeline/pexels_key.txt` (free stock). Env vars work too (`OPENAI_API_KEY`, etc.). **Never ask the user to paste a key in chat** — create the empty file and open Notepad.

## Conventions

- `help.html` MUST be updated with any user-facing UX change.
- Restart the dashboard after editing `review.py`/`make_videos.py` (Python is imported at start; the HTML pages are read per-request).
- Caches: `pipeline/ai-visuals/` (images), `pipeline/polished-prompts/` (OpenAI prompt rewrites), `pipeline/infer-videos/`, `pipeline/stock/` — delete a scenario's entry to regenerate.
- Free image/text generation: Pollinations (keyless). `text.pollinations.ai` blocks browsers (Turnstile) — call it server-side; ~1 request per IP, retry on 429.
- ffmpeg drawtext: reference fonts by colon-free path (drive letters break the filtergraph); literal `%` breaks drawtext.
- Every build session ends with a "Next best slice" recommendation; the user replying "." means build it.
- Work on feature branches → PR. Don't stack-then-delete: merging a stacked chain = retarget the tip PR to main, merge it, ancestors auto-mark merged.
- No virality/monetization promises in any user-facing copy.
