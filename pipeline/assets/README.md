# Assets

- `Poppins-ExtraBold.ttf` — the modern caption font. Poppins is licensed under the
  SIL Open Font License 1.1 (free for commercial use, including bundling). Designed by
  Indian Type Foundry & Jonny Pinhorn. Source: Google Fonts.
- `JuliusSansOne-Regular.ttf` — the Scary Story title-card/cover font (family name
  "Julius Sans One"): thin display caps, tracked wide for the art-house horror
  poster look. SIL OFL 1.1. Designed by Luciano Vergara. Source: Google Fonts.
- `Creepster-Regular.ttf` — the previous Scary Story font (family name "Creepster"),
  kept for anyone who wants the campfire-horror look back via CATEGORY_BRANDING.
  SIL OFL 1.1. Designed by Sideshow. Source: Google Fonts.
- `IMFellEnglishSC-Regular.ttf` — the True History title-card/cover font (family name
  "IM FELL English SC"). SIL OFL 1.1. Digitized by Igino Marini from John Fell's
  17th-century types. Source: Google Fonts (upstream file `IMFeENsc28P.ttf`).

The pipeline copies these fonts into each render's temp folder and hands them to
libass/ffmpeg, so text looks identical on any machine without installing fonts
system-wide. Spoken captions always use Poppins for readability; the title card,
follow card, and thumbnail use the category's font from `CATEGORY_BRANDING` in
`../make_videos.py` (falling back to Poppins if a .ttf is missing).
