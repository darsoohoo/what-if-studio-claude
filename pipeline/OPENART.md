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
- PIPELINE WORK NEEDED ("clip-voiced beats"): for a lip-synced beat the
  voice track goes silent for that span (a silence chunk sized to the clip's
  line), the clip's audio passes through at full volume for that beat only
  (per-beat clip audio - today --clip-audio is global and quiet), and
  captions estimate word timings evenly across the clip's speech. The
  character caption tint/name flash keep working off the script's [Name] tag.
- Human QA: listen to openart-cast/canary2-mara-elvoice.mp4 - if the cloned
  voice reads close enough to Bella, ship; if not, try the 10s sample (2s
  may be thin for cloning) before judging.

Future upgrade: OpenArt character elements carry a `voice` field supporting
`provider: "elevenlabs"` + voiceId (seen in the form schema) — when Character
Builder reaches MCP, a character bound to the SAME ElevenLabs voice id the
pipeline casts would remove the cloning step entirely.

## Session workflow (until a skill wraps it)

Ask Claude: "lipsync <package>" → reads the script, picks hero dialogue
beats, reuses/creates portraits, generates Seedance Mini clips per line,
downloads to the staging dir as refv-NN.mp4 + sets ref-choice, reports
credits spent (before/after via openart_account_get), then render as usual.
