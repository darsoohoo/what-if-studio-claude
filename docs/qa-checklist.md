# QA Checklist — Local Beta

Run before tagging a release. Boxes below reflect the **M4 QA hardening pass on 2026-07-04**, run against the current build (app + custom scenario builder) in a live browser via the preview harness.

## Static checks

- [x] `node --check app.js` passes
- [x] `git diff --check` clean

## Browser smoke test (open `index.html` directly — `file://`)

- [x] Page loads with no console errors (verified: error-level console empty after reload)
- [x] Browse the library; search narrows results; category chips filter; count updates
- [x] "New Scenario Seed" rotates through all 8 categories on repeated presses; "Copy seed" works
- [x] Select a scenario → workspace shows premise, safety note, tags
- [x] Change platform / runtime / voice → Generate Package reflects all three
- [x] All 6 package tabs render; "Copy this section" and "Copy full package" work
- [x] Export `.txt` / `.srt` / `.json`; SRT timestamps sum to the chosen runtime
- [x] Save to an occupied slot asks before overwriting
- [x] Reload → queue, statuses, notes, and custom scenarios persist
- [x] Slot "Clear" and header "Reset all local data" confirm before acting

## Custom scenario builder (new)

- [x] Dialog uses native `<dialog>` with `aria-labelledby` (focus trap + Escape-to-close are native)
- [x] Opening moves focus to the first field; closing returns focus to the trigger
- [x] All fields have labels (title/premise/category/glyph/tags via `<label>`, beats via `aria-label`)
- [x] Empty/short submit shows a friendly inline error (`role=alert`), never crashes
- [x] Created scenarios persist, carry a "Custom" flag, and are deletable

## Accessibility

- [x] No unnamed interactive controls (audited all button/a/input/select/textarea)
- [x] Skip link present and targets an existing `#library`
- [x] Visible focus ring via `:focus-visible` on every interactive element
- [x] Category chips, platform, runtime are `role=radiogroup` with roving tabindex (exactly one `tabindex=0` each) and arrow-key nav
- [x] Package tabs use `role=tab`/`aria-selected` with roving tabindex and arrow-key nav
- [x] Status messages announced via `aria-live` (storageBadge, seedText, libraryCount, actionStatus)
- [x] Decorative glyphs (`card-glyph`, `banner-glyph`, `brand-mark`, `empty-glyph`) are `aria-hidden`
- [x] **Fixed:** `prefers-reduced-motion` now disables smooth scroll, transitions, and caption/pop animations (CSS media query + JS `scrollIntoView` guard)
- [x] **Fixed:** `--text-faint` raised #6b7290 → #7d87a3 (3.8:1 → 5.02:1 on panel bg, passes WCAG AA for small text)

## Responsive (verified via viewport resize)

- [x] 1366×768 — three-column layout, no horizontal overflow
- [x] 820×1180 — two columns, queue full-width, no overflow
- [x] 390×844 — single column, stacked controls, no overflow; builder dialog fits (355px)

## Copy safety audit

- [x] No text promises virality, growth, follower counts, or income (only footer *disclaimer* mentions growth/monetization)
- [x] No fake analytics, bot, or engagement-automation features or claims ("fake" appears only inside scenario narration)
- [x] Speculative content carries framing notes; footer states the fiction disclaimer
- [x] No tracking scripts, remote requests, or external dependencies (grep for `http`/`fetch`/`cdn` in app files: no matches)

## Storage failure handling

- [x] Mid-session localStorage failure (quota/privacy) degrades to in-memory without throwing to the caller
- [x] Storage badge flips to "Memory only — export to keep work" on degradation
