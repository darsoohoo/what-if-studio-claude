# Brand kit

Cosmic purple identity matching the app's look and the caption style (Poppins ExtraBold).

| File | Size | Use it for |
|------|------|-----------|
| `profile-c-cosmic.jpg` | 768×768 | **Channel profile picture** (YouTube, TikTok, X) — the chosen one |
| `profile-a-gradient.png` / `profile-b-dark.png` | 768×768 | Alternate profile options |
| `banner-youtube.png` | 2560×1440 | **YouTube channel banner.** Title + tagline sit inside the 1546×423 device-safe area, so they survive every crop: TV gets the full art, desktop a wide strip, phones just the safe area. |
| `banner-x-header.png` | 1500×500 | X/Twitter profile header (center crop of the same art) |

TikTok has no banner — the profile picture and video covers carry the brand there.

## How they were made (regenerating)

Background: free Pollinations image (`https://image.pollinations.ai/prompt/<urlencoded>?width=2560&height=1440&nologo=true&seed=N` — the service caps at 1024×576, upscaled 2.5× with ffmpeg lanczos, which nebula art tolerates well). Prompt family: *"ultrawide deep space nebula, swirling purple magenta violet cosmic clouds with cyan highlights, dark starry sky, cinematic"*.

Text: ffmpeg `drawtext` with `pipeline/assets/Poppins-ExtraBold.ttf` (reference the font by a **colon-free relative path** — a drive letter breaks the filtergraph), white fill, dark border + drop shadow, centered in the safe area.
