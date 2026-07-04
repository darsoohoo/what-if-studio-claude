# Content Quality Rubric — Starter Scenarios

Every scenario in `scenarioBank` must pass all of the following before it ships. This rubric was applied to all 24 starter scenarios.

## Structure (hard requirements)

| Check | Requirement |
|---|---|
| Fields | `id`, `category`, `title`, `image`, `premise`, `tags`, `safety`, `hooks`, `beats`, `shotList`, `captions`, `thumbnails` — all present and non-empty |
| Hooks | Exactly 3, each speakable in ≤ 2 seconds of screen time, each a different angle (curiosity / authority / dread-or-humor) |
| Beats | 5 beats: setup → escalation → twist → grounding → payoff. Beat 5 must land a quotable closing line |
| Shot list | 5–6 shots, each achievable with stock footage, simple graphics, or a phone — no budget assumptions |
| Captions | 3 options, platform-neutral (hashtags are appended per platform at generate time) |
| Thumbnails | 3 title-card texts, ≤ 5 words each, readable at thumbnail size |

## Writing quality

- **The hook is the product.** If the first line doesn't create an open question, rewrite it.
- **One real anchor per scenario.** Every scenario includes at least one true, checkable fact (Wörgl's expiring money, the Blockbuster meeting, the Bloop, saccadic masking…). Pure vibes don't hold attention past the first video.
- **The payoff reframes, it doesn't just conclude.** The last beat should make the viewer see the premise differently, not summarize it.
- **30-second cut must survive.** The first 3 beats must work as a standalone story, because the 30s runtime uses only those.

## Safety framing (required, enforced per scenario in the `safety` field)

- Speculation is labeled as speculation; real facts are separated from fiction explicitly in the beats ("that part is documented", "this part is fiction").
- Sensitive topics (real deaths, health topics, scams, sleep paralysis) keep a respectful, protective, non-panic tone and include reassurance or a defensive takeaway where relevant.
- No real living person is accused, identified, or defamed; alternate history about public figures sticks to their public careers.
- No health, financial, or legal advice; fictional "get rich" angles are flagged as fiction.
- No claims of guaranteed virality, growth, or monetization anywhere in scenario copy or UI.

## Category balance (M3 exit criteria)

- 24 scenarios total, exactly 3 per category ✅
- Every category mixes tones (at least one playful and one eerie entry) so the first screen doesn't read as a single mood ✅
- Seed rotation covers all 8 categories with 4 seeds each, cycling category-first so consecutive presses never repeat a category ✅
