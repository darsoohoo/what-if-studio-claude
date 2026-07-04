# Assets

- `Poppins-ExtraBold.ttf` — the modern caption font. Poppins is licensed under the
  SIL Open Font License 1.1 (free for commercial use, including bundling). Designed by
  Indian Type Foundry & Jonny Pinhorn. Source: Google Fonts.

The pipeline copies this font into each render's temp folder and hands it to libass, so
captions look identical on any machine without installing fonts system-wide.

To change the caption font, drop a different `.ttf` here and update `CAPTION_FONT_FILE`
and `CAPTION_FONT_NAME` at the top of `../make_videos.py`.
