# QA Checklist — Local Beta

Run before tagging a release. All items verified against the current build.

## Static checks

- [ ] `node --check app.js` passes
- [ ] `git diff --check` clean

## Browser smoke test (open `index.html` directly — `file://`)

- [ ] Page loads with no console errors in Chrome and Edge
- [ ] Browse the library; search narrows results; category chips filter; count updates
- [ ] "New Scenario Seed" rotates through all 8 categories on repeated presses; "Copy seed" works
- [ ] Select a scenario → workspace shows premise, safety note, tags
- [ ] Change platform / runtime / voice → Generate Package reflects all three (meta line, beat count, hashtags, outro)
- [ ] All 6 package tabs render; "Copy this section" and "Copy full package" work
- [ ] Export `.txt` downloads; export `.srt` downloads with timestamps summing to the chosen runtime
- [ ] Save to an occupied slot asks before overwriting
- [ ] Reload the page → queue, statuses, and notes persist (localStorage mode)
- [ ] Slot status changes and tracker notes persist after reload
- [ ] Slot "Clear" and header "Reset all local data" both confirm before acting, then work
- [ ] Storage badge shows "Saving locally" normally, "Memory only" when localStorage is blocked

## Accessibility

- [ ] Full workflow completable with keyboard only (tab, arrows, enter/space)
- [ ] Skip link appears on first Tab and jumps to the library
- [ ] Visible focus ring on every interactive element
- [ ] Category chips, platform, and runtime are radiogroups with arrow-key navigation
- [ ] Package tabs use `role=tab`/`aria-selected` with arrow-key navigation
- [ ] Status messages announced via `aria-live` (save, copy, export, reset)
- [ ] Screen reader spot check: cards, controls, and slots have sensible names

## Responsive

- [ ] 1366×768 — three-column layout, no overflow
- [ ] 820×1180 — two columns, queue full-width
- [ ] 390×844 — single column, stacked controls, touch-sized buttons

## Copy safety audit

- [ ] No text promises virality, growth, follower counts, or income
- [ ] No fake analytics, bot, or engagement-automation features or claims
- [ ] Speculative content carries framing notes; footer states the fiction disclaimer
- [ ] No tracking scripts, remote requests, or external dependencies (grep for `http` in app files)
