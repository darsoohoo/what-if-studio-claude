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

## Voice consistency (open decision, next canary)

Options, best first:
a. **Audio element per line**: upload the ElevenLabs v3 line audio as the
   audio element → if Seedance performs it verbatim, mute the clip in the mix
   and the pipeline's own EL track stays the voice (captions stay perfect,
   lips match because same audio). Blocker: no programmatic upload via MCP —
   `openart_upload_pick` mounts a browser widget (worked: `ready: true`);
   per-line uploads are manual. Test whether the widget renders in the
   desktop app; if per-line is too manual, fall back to (b).
b. **Voice sample per character**: upload ONE 10s ElevenLabs sample per cast
   character (one-time, via widget or openart.ai uploads page) → Seedance
   clones that voice per clip; the clip's own audio IS the line. Pipeline
   change needed: "clip-voiced beat" = voice track goes silent for that
   span, clip audio passes through at full volume, captions estimated from
   clip duration.
c. **Prompt-only voice** (what the canary did): Seedance invents a fitting
   voice per clip. Zero setup, voice drifts between clips/videos.
d. Future: OpenArt character elements carry a `voice` field supporting
   `provider: "elevenlabs"` + voiceId (seen in the form schema) — Character
   Builder isn't MCP-exposed yet, but a character created in their web UI
   with the SAME ElevenLabs voice the pipeline casts would make voices match
   exactly across narration and lips. Revisit when MCP exposes characters.

## Session workflow (until a skill wraps it)

Ask Claude: "lipsync <package>" → reads the script, picks hero dialogue
beats, reuses/creates portraits, generates Seedance Mini clips per line,
downloads to the staging dir as refv-NN.mp4 + sets ref-choice, reports
credits spent (before/after via openart_account_get), then render as usual.
