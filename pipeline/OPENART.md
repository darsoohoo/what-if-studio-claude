# OpenArt integration notes (talking characters / lip sync)

Verified live 2026-07-15 against the OpenArt MCP (`https://mcp.openart.ai/mcp`,
OAuth via the claude.ai connector — attaches to Claude sessions automatically;
no API key exists, so the render pipeline cannot call it headlessly; Claude
orchestrates and drops finished clips into the per-beat video slots).

## The model that matters

**Seedance 2.0 (Mini / Fast / full) `element2video`** accepts image + video +
**audio** elements. An image element pins the character's identity; the prompt
says what they do and SAY; with `generateAudio: true` the character speaks the
line with moving lips. An audio element (wav/mp3, 2–15s) gives the subject a
specific VOICE ("the woman in image 1 speaks with this voice").

Canary result (Mini, 480p, 4s, 9:16, 90 credits total): cinematic frame
matching the cast look exactly, lips articulating the whispered line, quiet
whisper audio in the track. Quality at 480p is fine for 1080x1920 phone video.

## Credit costs (measured 2026-07-15, defaults change per config)

- Portrait image: Kling 3 Omni text2image 1k = **10 cr** (Nano Lite 15, Seedream 15)
- Lip-synced line: Seedance 2.0 Mini element2video 9:16 + audio:
  **80 cr @ 480p/4s, 160 cr @ 720p/4s** (duration min 4s, max 15s; price scales)
- Fast tier ≈ ×1.75, full Seedance ≈ ×2 of Mini. Kling 3 Omni element2video
  (175 cr) has NO audio elements. Balance at time of writing: 3910 cr.

## The reference-format gotcha (cost two failed submits to learn)

Seedance/Kling are "strict reference" models: `visualReferences` entries need
metadata with **snake_case** keys (`media_type`, `width`, `height`,
`file_size_bytes`, `format`). Don't hand-build it — call
`openart_upload_metadata_get(mediaUrl, mediaType, label)` with ANY OpenArt CDN
URL (works for generated creations, not just uploads) and it returns a
ready-to-use `visualReference` object. Failed submits cost nothing.

## Cost-efficient production flow (the design)

1. **Cast portraits once per character**, cached in `pipeline/openart-cast/`
   (`<scenario-or-global>-<name>.png` + the CDN URL alongside). Reused across
   every video the character appears in: 10 cr one-time per character.
2. **Lip-sync only hero dialogue shots** (2–4 per video, where the camera is
   on the speaker's face); reaction/wide/(silence) beats keep the existing
   free/cheap visual paths. A 3-hero-line video ≈ 240 cr @480p / 480 cr @720p.
3. Clips download into the package staging dir as `refv-NN.mp4` (radio=video):
   they play as-is, are never re-billed, and survive re-renders.
4. Cache key: (character portrait URL + line text + duration) — regenerating a
   video re-bills nothing unless a line changed.

## Voice consistency — SETTLED by canary #2 (2026-07-15, 80 cr)

Uploaded a real ElevenLabs v3 line (Bella whispering) as the audio element:
Seedance **re-performs the line in that voice** rather than copying the
waveform (peak normalized cross-correlation 0.232 vs our source — a clone,
not a copy). The upload widget DOES render in the Claude desktop app, so
uploads are drag-and-drop.

**Adopted architecture: one voice sample per character, clip audio IS the
line.**
- One ~10s ElevenLabs sample per cast character, uploaded once (drag into the
  widget), cached: `openart-cast/<name>-voice.mp3` + its upload id/URL in
  `openart-cast/cast.json`. Reused for every line, every video. Voice stays
  consistent because every clip clones the same sample.
- Each hero dialogue beat generates with portrait + voice sample + the line
  in the prompt ("says exactly: ..."). The clip's own audio IS the spoken
  line, lips already perfect.
- **Clip-voiced beats: BUILT and verified 2026-07-15.** Mark beats in
  `lipsync.json` in the staging dir ({"<1-based row>": true}); the beat must
  also have its refv-NN.mp4 staged with the radio on video. The renderer
  then: holds silence in the voice track for exactly the clip's length,
  plays that beat's clip audio at full volume (others follow --clip-audio),
  estimates caption word timings across the clip's detected speech region
  (silencedetect), keeps the speaker tint + — NAME flash from the [Name]
  tag, and anchors the beat span at the clip's first frame so lips never
  shift. Verified end-to-end: canary2 clip as beat 2 of a 4-row dialogue
  trailer - clip on screen, captions tinted, no double-voice.
- Canary voice QA: PASSED by Darren ("canary voice looks good").

Future upgrade: OpenArt character elements carry a `voice` field supporting
`provider: "elevenlabs"` + voiceId (seen in the form schema) — when Character
Builder reaches MCP, a character bound to the SAME ElevenLabs voice id the
pipeline casts would remove the cloning step entirely.

## Session workflow (until a skill wraps it)

Ask Claude: "lipsync <package>" → reads the script, picks hero dialogue
beats, reuses/creates portraits, generates Seedance Mini clips per line,
downloads to the staging dir as refv-NN.mp4 + sets ref-choice, LOGS EVERY
generation to the Spend ledger:
  python -c "import make_videos as mv; mv.record_spend('openart','talking clip',None,'seedance-2-mini','<scenarioId>',credits=80)"
(credits are the source of truth; USD is estimated at the plan rate,
override via openart_rate.txt), verifies the total against
openart_account_get before/after, then renders as usual.

## Voice acting (field feedback 2026-07-15: "sounds like someone reading a book")

Three levers, all applied:
1. **v3 Creative mode**: dialogue chunks synthesize with voice_settings
   {"stability": 0.0} - v3's emotional register. The default read IS the
   audiobook voice. (previous_text/next_text are NOT supported on v3 yet.)
2. **Acted text**: the trailer writer now writes SPEECH under stress, not
   prose - false starts (I- I hear it), stutters, trail-offs, repeats,
   one CAPS word max, cue combos and mid-line non-verbals ([gasps],
   [shaky breath], [swallows hard]).
3. **Better clone source**: openart-cast/mara-voice-sample.mp3 is a 10.9s
   emotionally varied v3-Creative sample for Seedance voice cloning
   (replaces the flat 2s whisper - re-upload via the widget and update
   cast.json's voice_upload_id/voice_url). Seedance clip prompts should
   also carry voice direction: "voice trembling and breathy, ragged
   breathing between words, genuinely frightened - not performed".

A/B/C listening set in openart-cast/voice-tests/: a-default.mp3 (old),
b-creative.mp3 (stability 0), c-acted.mp3 (stability 0 + acted text).

## 🎨 OpenArt visuals mode (fulfillment procedure)

The Produce page's "OpenArt AI video" radio stages `openart-request.json` in
the package's staging dir (the render can't call the MCP itself - OAuth
lives with Claude). When Darren says "fulfill the OpenArt request":

1. Find the newest `pipeline/produce/*/openart-request.json` with
   status "requested". Confirm the estimated credits with Darren first if
   the total exceeds 500.
2. For each row: generate a Seedance Mini `element2video` clip
   (resolution/model from the request, 9:16, duration 4-5s,
   generateAudio true). Use the row's `prompt` + the trailer look; when a
   cast character appears in the row's spoken line or prompt, attach their
   cached portrait (openart-cast/cast.json) as an image element for
   identity. These are ambience clips, NOT talking clips - do not attach
   voice samples and do NOT mark lipsync.json (the TTS voice track carries
   the lines; talking hero clips are the separate "lipsync it" flow, which
   can layer on top afterward by overwriting specific rows).
3. Respect the 2-concurrent generation limit; log EVERY clip to the spend
   ledger as it completes; download each to refv-NN.mp4 (curl with a
   browser User-Agent - urllib gets 403) and set ref-choice video for
   every row.
4. Set the request's status to "fulfilled" (+ credits spent), then render
   via the CLI with the request's render flags (--trailer / --elevenlabs
   as recorded), verify the log, and report per-clip + total spend with
   the account balance before/after.

## First full production (Romeo & Juliet AI-English, 2026-07-16, 1000 cr)

Whole-package pattern, verified end-to-end: 2 portraits (Kling 3 Omni,
10 cr each) + 7 ambience clips (both portraits as identity elements) +
5 hero talking clips (portrait + per-character voice sample + "says
exactly" line + voice direction), all Seedance Mini 480p 9:16 4s (5s for
the long cold-open line, 100 cr). lipsync.json marks the 5 hero rows;
ref-choice.json puts all 12 rows on video; render with
`--backgrounds produce/<staging> --trailer --elevenlabs --score <genre>
--clip-audio 0.2`. Ledger matched openart_account_get exactly.

Operational notes:
- The concurrency limit is ~3 in-flight (not 2) and fluctuates; a
  PARALLEL_LIMIT_EXCEEDED submit costs nothing - just retry after a
  poll shows a slot freed.
- Voice samples: ~13 s ElevenLabs v3-Creative (stability 0) in the
  video's own language/register, one per character, cast with the SAME
  EL voice the renderer picks (Charlie/Bella) so clip-voiced and
  TTS-voiced lines match. Seedance caps audio elements at 15 s.
- One upload widget with minFiles=2 collects both samples in a single
  user action; upload ids + URLs land in openart-cast/cast.json.
