/* ============================================================
   What If Studio — assistant.js
   The studio assistant chat, shared by every page. Static and
   local-only: injects its own UI and styles, works from file://
   with no server (offline commands + built-in FAQ), and gets
   smarter when the local dashboard is running (/api/chat).

   Page-specific behavior comes from window.assistantHost
   (set by app.js on the Studio page BEFORE this script loads):
     { page, capabilities, getContext(), parseIntent(text),
       runAction(action) -> Promise<string|null> }
   Pages without a host (Videos/Produce/Spend/Help) get the
   built-in dashboard host: Q&A plus page navigation.
   ============================================================ */

"use strict";

(() => {

  /* file:// (the Studio opened directly) talks to the dashboard by
     absolute address; server-hosted pages use their own origin. */
  const API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:8765" : "";
  const NAV_TARGETS = { studio: "/studio/", videos: "/", produce: "/produce", spend: "/spend", help: "/help" };

  /* ---------- built-in dashboard host (no window.assistantHost) ---------- */

  function dashboardPage() {
    const path = window.location.pathname.replace(/\/+$/, "") || "/";
    if (path.endsWith("/studio")) return "studio";
    if (path === "/produce") return "produce";
    if (path === "/spend") return "spend";
    if (path === "/help" || /help\.html$/.test(path)) return "help";
    if (/index\.html$/.test(path) && window.location.protocol === "file:") return "studio";
    return "videos";
  }

  function makeDashboardHost() {
    const page = dashboardPage();
    return {
      page,
      capabilities:
        "On this page I answer questions — how rendering works, where keys go, " +
        "what the pages do — check on your renders (“is my video done?”), fetch a " +
        "post kit (“give me the caption for my newest video”), flag what went out " +
        "(“mark it posted”), and jump around for you: “go to studio”, “go to " +
        "videos”, “go to produce”, “go to spend”.\n" +
        "Opening scenarios, changing settings, and making new videos happen in the " +
        "Studio — say “go to studio” and I'll run those there.",
      getContext() {
        const ctx = { page, pageTitle: document.title };
        const pkg = document.getElementById("pkgSelect");
        if (pkg && pkg.selectedOptions[0] && pkg.selectedOptions[0].value) {
          ctx.selectedPackage = pkg.selectedOptions[0].textContent;
        }
        return ctx;
      },
      parseIntent(text) {
        const t = text.toLowerCase();
        const nav = t.match(/^(?:go to|take me to|open|show me|show)\s+(?:the\s+)?(studio|videos?|produce|spend|help|how[- ]to|guide)\b/);
        if (nav) return { action: { name: "navigate", args: { page: nav[1] } } };
        if (/what('?s| is) (this|here)|which page|where am i/.test(t)) {
          return { reply: `You're on the ${page[0].toUpperCase() + page.slice(1)} page. Ask me anything about it, or say “go to …” to move around.` };
        }
        return null;
      },
      async runAction(action) {
        const args = (action && action.args) || {};
        if (action && action.name === "navigate") {
          let key = String(args.page || "").toLowerCase();
          if (/help|how|guide/.test(key)) key = "help";
          if (key.startsWith("video")) key = "videos";
          const target = NAV_TARGETS[key];
          if (!target) return "I can go to Studio, Videos, Produce, Spend, or Help.";
          if (key === page) return "You're already there.";
          window.location.href = target;
          return `Heading to ${key[0].toUpperCase() + key.slice(1)}…`;
        }
        return "That's a Studio action — say “go to studio” and ask me again there.";
      }
    };
  }

  /* ---------- shared FAQ (works everywhere, fully offline) ---------- */

  const KB = [
    { k: ["render", "watcher", "video made", "actually make", "mp4", "downloads"],
      a: "Rendering happens outside the app: “Generate + Export for render” downloads a queue .json, and the watcher (started by Start-What-If-Studio, or pipeline/start-watcher.bat) spots it in Downloads and renders a 1080×1920 video with voiceover, captions, visuals, music, a thumbnail, and a post kit. Finished videos appear on the Videos page." },
    { k: ["start everything", "helper", "dashboard offline", "the bat", "double-click"],
      a: "Double-click Start-What-If-Studio.bat in the project folder once — it starts the local dashboard (127.0.0.1:8765) and the render watcher. The Studio app itself works without it; the helper adds AI writing, my smart answers, and the Videos/Produce/Spend pages." },
    { k: ["api key", "openai", "elevenlabs", "pexels", "keys go"],
      a: "API keys are optional, one per file in the pipeline folder: openai_key.txt (better AI writing), elevenlabs_key.txt (premium voices), tryinfer_key.txt (paid AI video), pexels_key.txt (free stock). Without keys, free services are used. Never paste keys into chats — just drop them in the files." },
    { k: ["runtime", "length", "how long", "duration", "seconds"],
      a: "Runtimes: 30s (3 tight beats), 60s (standard 5 beats), 90s (room to breathe), 3 min (extended). Pick it in the Studio's Package settings — the narration length is what actually sets the video length." },
    { k: ["voices", "voice style", "narrator", "tts", "delivery"],
      a: "Three delivery styles: Calm Narrator, High-Energy Storyteller, and Deadpan Documentarian — picked in the Studio's Package settings. With an ElevenLabs key the render maps them to premium voices (Adam, Callum, George); otherwise free TTS is used. The Produce page lets you pick an exact ElevenLabs voice per render." },
    { k: ["hashtag", "posting", "post kit", "caption", "tiktok", "shorts", "reels", "platform"],
      a: "One package works on TikTok, YouTube Shorts, and Reels — the vertical 9:16 cut is platform-neutral. Per-platform hashtags and captions come with the rendered video's post kit, not the package. Ask me “give me the caption for my newest video” and I'll fetch it. Posting is always manual and up to you." },
    { k: ["custom", "own scenario", "builder", "write it for me", "draft"],
      a: "In the Studio, “+ Create your own scenario” opens the builder: give it a title, and “Write it for me” drafts the premise and beats with AI (needs the Studio helper running). Everything stays editable. Or just tell me “make a video about …” on the Studio page and I'll do the whole thing." },
    { k: ["edit the script", "edit script", "change the title", "rename", "typo", "cover text"],
      a: "On the Produce page, expand “Show the script” — you can edit the title (it's also the video's cover text), the spoken hook, every beat, and the outro. Save, and the next render speaks and captions the new version; the package dropdown picks up the new title too." },
    { k: ["delete", "remove scenario"],
      a: "Open a custom scenario in the Studio and use its Delete button in the banner. Built-in scenarios can't be deleted. “Reset all local data” (Studio, top right) clears all custom scenarios and the seed rotation — I never do that for you." },
    { k: ["save", "storage", "lose", "persist", "local data"],
      a: "Custom scenarios and the seed rotation save to the browser's local storage — nothing leaves your device. If the Studio badge says “Memory only”, the browser is blocking storage for file:// pages, so export packages to keep them." },
    { k: ["export", "srt", "txt", "json", "subtitle"],
      a: "After generating in the Studio: Export .txt (full package), .srt (timed subtitles), or .json (the render queue format — export again any time to re-render). Copy buttons grab a section or the whole package." },
    { k: ["seed", "idea", "angle", "inspiration"],
      a: "“New Scenario Seed” (Studio top bar) rotates through fresh prompts across all 10 categories — including Scary Story and True History premises. Or ask me on the Studio page: “give me an idea” — then “make a video about it”." },
    { k: ["music", "thumbnail", "visuals", "images", "ai visuals", "clips"],
      a: "The render pipeline handles visuals, music, and thumbnails automatically — per-beat visuals, mood-matched music, word-synced captions. The Produce page gives you per-beat control: your own clips, AI images, prompts, and premium AI video." },
    { k: ["how much", "cost", "spend", "money", "is it free"],
      a: "The app and the default pipeline are free (free TTS, free image generation). Paid extras are opt-in via keys: OpenAI writing, ElevenLabs voices, Infer AI video. The Spend page tracks what the paid services cost you." },
    { k: ["privacy", "tracking", "account", "login", "server"],
      a: "Everything runs locally: no server on the internet, no account, no tracking, no remote content. The optional helper runs only on your machine at 127.0.0.1. Nothing is posted anywhere automatically." },
    { k: ["pages", "videos page", "produce page", "spend page", "sidebar"],
      a: "The sidebar pages: Studio (build packages), Videos (review + post-kit for finished renders), Produce (per-beat visuals, voices, script edits, re-renders), Spend (API costs), and the How-to guide. Say “go to …” and I'll take you there." },
    { k: ["scary story", "scary stories", "true history", "horror", "creepy", "story categories", "categories"],
      a: "Besides the what-if categories there are two story categories: Scary Story (narrative horror — the trapped diver, the 3:33 doorbell) and True History (real documented events — the dancing plague, the Emu War). Their videos brand themselves automatically: dark or archival visuals, their own title-card fonts, a matching follow card and outro, and the right hashtags in the post kit. On the Studio page, say “make a scary story about …” or “make a true history video about …” and I'll draft it straight into the right category." }
  ];

  function kbAnswer(text) {
    const t = " " + String(text).toLowerCase() + " ";
    let best = null, bestScore = 0;
    KB.forEach(entry => {
      const score = entry.k.reduce((n, kw) => n + (t.includes(kw) ? (kw.length > 5 ? 2 : 1) : 0), 0);
      if (score > bestScore) { best = entry; bestScore = score; }
    });
    // A single weak keyword isn't a match - hand those to the AI tier.
    return bestScore >= 2 ? best.a : null;
  }

  /* ---------- UI (injected so every page gets it for free) ---------- */

  const CSS = `
.assistant-fab{position:fixed;right:18px;bottom:18px;z-index:900;width:52px;height:52px;border-radius:50%;
  border:1px solid var(--border-strong,#3a4160);background:linear-gradient(135deg,var(--accent,#8b7bff),#6a5ae0);
  color:#fff;font-size:22px;line-height:1;cursor:pointer;box-shadow:0 6px 24px rgba(0,0,0,.35);}
.assistant-fab:hover{background:linear-gradient(135deg,var(--accent-strong,#a99bff),#7a6af0);}
.assistant-panel{position:fixed;right:18px;bottom:80px;z-index:900;width:min(370px,calc(100vw - 24px));
  height:min(540px,calc(100vh - 104px));display:flex;flex-direction:column;background:var(--bg-raised,#131624);
  color:var(--text,#e8eaf2);border:1px solid var(--border-strong,#3a4160);border-radius:12px;
  box-shadow:0 6px 24px rgba(0,0,0,.35);overflow:hidden;font-size:14px;text-align:left;}
.assistant-panel[hidden]{display:none;}
.assistant-head{display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid var(--border,#262b40);}
.assistant-title{font-weight:600;font-size:14px;}
.assistant-mode{margin-left:auto;font-size:11px;padding:2px 9px;border-radius:999px;
  border:1px solid var(--border-strong,#3a4160);color:var(--text-dim,#9aa1b9);cursor:default;}
.assistant-mode.on{color:var(--good,#4cd6a4);border-color:var(--good,#4cd6a4);}
.assistant-close{background:none;border:none;color:var(--text-dim,#9aa1b9);font:inherit;font-size:14px;padding:2px 6px;cursor:pointer;}
.assistant-close:hover{color:var(--text,#e8eaf2);}
.assistant-log{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;}
.assistant-msg{max-width:88%;padding:8px 11px;border-radius:12px;font-size:13.5px;line-height:1.45;
  white-space:pre-wrap;overflow-wrap:break-word;}
.assistant-msg.user{align-self:flex-end;background:var(--accent,#8b7bff);color:#fff;border-bottom-right-radius:4px;}
.assistant-msg.bot{align-self:flex-start;background:var(--bg-inset,#0e1120);border:1px solid var(--border,#262b40);border-bottom-left-radius:4px;}
.assistant-msg.busy{color:var(--text-dim,#9aa1b9);font-style:italic;}
.assistant-chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 12px 8px;}
.assistant-chip{font:inherit;font-size:12px;padding:4px 11px;border-radius:999px;border:1px solid var(--border-strong,#3a4160);
  background:var(--bg-inset,#0e1120);color:var(--text-dim,#9aa1b9);cursor:pointer;}
.assistant-chip:hover{color:var(--text,#e8eaf2);border-color:var(--accent,#8b7bff);}
.assistant-form{display:flex;gap:8px;padding:10px 12px;border-top:1px solid var(--border,#262b40);}
.assistant-form input{flex:1;font:inherit;font-size:13.5px;color:var(--text,#e8eaf2);background:var(--bg-inset,#0e1120);
  border:1px solid var(--border-strong,#3a4160);border-radius:8px;padding:8px 11px;min-width:0;}
.assistant-copy{display:block;margin-top:8px;font:inherit;font-size:12px;padding:4px 11px;border-radius:999px;
  border:1px solid var(--border-strong,#3a4160);background:var(--bg-raised,#131624);color:var(--text-dim,#9aa1b9);cursor:pointer;}
.assistant-copy:hover{color:var(--text,#e8eaf2);border-color:var(--accent,#8b7bff);}
.assistant-send{font:inherit;font-weight:600;font-size:13px;padding:8px 14px;border-radius:8px;border:none;
  background:linear-gradient(135deg,var(--accent,#8b7bff),#6a5ae0);color:#fff;cursor:pointer;}
@media (max-width:700px){.assistant-panel{right:12px;bottom:76px;}.assistant-fab{right:12px;bottom:14px;}}
`;

  function build(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text) node.textContent = text;
    return node;
  }

  const chat = { history: [], busy: false, greeted: false, lastKitVideo: null, host: null, ui: {} };

  /* The conversation follows you between pages (same tab): history, the
     greeting state, and which video "it" refers to ride in sessionStorage.
     Guarded - if storage is blocked (some file:// setups), chat just
     resets per page like before. */
  const STORE_KEY = "wis.assistant.v1";

  function saveChatState(open) {
    try {
      window.sessionStorage.setItem(STORE_KEY, JSON.stringify({
        history: chat.history.slice(-30),
        greeted: chat.greeted,
        lastKitVideo: chat.lastKitVideo || null,
        open: open !== undefined ? open : !chat.ui.panel.hidden
      }));
    } catch (err) { /* storage blocked - non-fatal */ }
  }

  function loadChatState() {
    try {
      return JSON.parse(window.sessionStorage.getItem(STORE_KEY) || "null");
    } catch (err) {
      return null;
    }
  }

  function addMsg(role, text, busy = false) {
    const msg = build("div", `assistant-msg ${role}${busy ? " busy" : ""}`, text);
    chat.ui.log.appendChild(msg);
    chat.ui.log.scrollTop = chat.ui.log.scrollHeight;
    return msg;
  }

  /* ---------- shared actions (work on every page) ---------- */

  function ago(epochSeconds) {
    const mins = Math.max(0, Math.round((Date.now() / 1000 - epochSeconds) / 60));
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins} min ago`;
    const hours = Math.round(mins / 60);
    if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
    const days = Math.round(hours / 24);
    return `${days} day${days === 1 ? "" : "s"} ago`;
  }

  /* "Is my video done?" - render progress + the newest finished videos,
     straight from the dashboard's own APIs. */
  async function checkRenders() {
    let status, videos;
    try {
      [status, videos] = await Promise.all([
        fetch(API_BASE + "/api/produce/render-status").then(r => r.json()),
        fetch(API_BASE + "/api/videos").then(r => r.json())
      ]);
    } catch (err) {
      throw new Error("dashboard-offline");
    }
    const parts = [];
    if (status && status.running) {
      parts.push(`🎬 A render is going right now (${status.label || "one video"}) — it lands on the Videos page when it's done.`);
    } else if (status && status.label) {
      parts.push(status.ok
        ? `The last dashboard render (${status.label}) finished ✓.`
        : `The last dashboard render (${status.label}) stopped without finishing — the Produce page log has the details.`);
    }
    const list = Array.isArray(videos) ? videos.slice().sort((a, b) => (b.mtime || 0) - (a.mtime || 0)) : [];
    if (list.length) {
      const newest = list.slice(0, 3).map(v =>
        `• ${v.title || v.name} — ${ago(v.mtime)}${v.uploaded ? " · posted ✓" : ""}`);
      parts.push(`Newest of your ${list.length} finished video${list.length === 1 ? "" : "s"}:\n${newest.join("\n")}`);
    } else {
      parts.push("No finished videos yet — export a package in the Studio and the watcher renders it in a few minutes.");
    }
    if (chat.host.page !== "videos" && list.length) parts.push("Say “go to videos” to watch and grab the post kits.");
    return parts.join("\n");
  }

  async function fetchVideos() {
    let videos;
    try {
      videos = await fetch(API_BASE + "/api/videos").then(r => r.json());
    } catch (err) {
      throw new Error("dashboard-offline");
    }
    return Array.isArray(videos) ? videos.slice().sort((a, b) => (b.mtime || 0) - (a.mtime || 0)) : [];
  }

  /* Loose title match against the finished-video list; "" / "newest" /
     "it" pick the default (the last post kit fetched, else the newest). */
  function resolveVideo(list, want) {
    want = String(want || "").trim().toLowerCase();
    if (!want || /^(newest|latest|last|my|it|that|this)\b/.test(want)) {
      return (chat.lastKitVideo && list.find(v => v.name === chat.lastKitVideo)) || list[0];
    }
    const stop = new Set(["the", "a", "an", "my", "video", "for", "of", "what", "if", "one"]);
    const words = want.replace(/[^a-z0-9\s]/g, " ").split(/\s+/).filter(w => w && !stop.has(w));
    if (!words.length) return list[0];
    let best = null, bestScore = 0;
    list.forEach(v => {
      const hay = String(v.title || v.name).toLowerCase();
      const score = words.reduce((n, w) => n + (hay.includes(w) ? 1 : 0), 0);
      if (score > bestScore) { best = v; bestScore = score; }
    });
    return best && bestScore >= Math.max(1, Math.ceil(words.length / 2)) ? best : null;
  }

  /* "Give me the caption for my newest video" - a finished video's post kit
     (caption + per-platform hashtags), ready to copy. Returns {text, copy}
     so the chat can attach a copy button. */
  async function getPostKit(args) {
    const list = await fetchVideos();
    if (!list.length) return "No finished videos yet — each render drops a post kit next to the video.";
    const video = resolveVideo(list, (args || {}).video);
    if (!video) return `I couldn't find a finished video matching “${String((args || {}).video || "").slice(0, 60)}” — try “post kit for my newest video”, or “go to videos” to browse.`;
    if (!video.post) return `“${video.title}” has no post kit file next to it (an older render?). New renders save one automatically.`;
    chat.lastKitVideo = video.name;   // "mark it posted" refers to this one
    const kit = video.post.trim();
    return {
      text: `Post kit for “${video.title}” (${ago(video.mtime)}):\n\n${kit}\n\nPosted it? Say “mark it posted” and I'll flag it.`,
      copy: kit
    };
  }

  /* "Mark it posted" - the same toggle as the Videos page, so the library
     always shows what's still waiting to go out. */
  async function markPosted(args) {
    const list = await fetchVideos();
    if (!list.length) return "No finished videos to mark yet.";
    const video = resolveVideo(list, (args || {}).video);
    if (!video) return `I couldn't find a finished video matching “${String((args || {}).video || "").slice(0, 60)}” — say “mark the … video as posted” with a word or two from its title.`;
    const posted = (args || {}).posted !== false;
    let reply;
    try {
      reply = await fetch(API_BASE + "/api/uploaded", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: video.name, uploaded: posted })
      }).then(r => r.json());
    } catch (err) {
      throw new Error("dashboard-offline");
    }
    if (!reply || reply.error) return `The dashboard couldn't update that: ${(reply && reply.error) || "unknown error"}.`;
    return posted
      ? `Marked “${video.title}” as posted ✓ — the Videos page shows it too. Nice one.`
      : `Un-marked “${video.title}” — it now counts as not posted yet.`;
  }

  /* Actions every page supports, checked before the host's own. */
  async function runAction(action) {
    if (action && action.name === "check_renders") return checkRenders();
    if (action && action.name === "get_post_kit") return getPostKit(action.args);
    if (action && action.name === "mark_posted") return markPosted(action.args);
    return chat.host.runAction(action);
  }

  /* ---------- engines ---------- */

  async function ping() {
    const badge = chat.ui.mode;
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 2000);
      await fetch(API_BASE + "/api/videos", { signal: controller.signal });
      clearTimeout(timer);
      badge.textContent = "AI online";
      badge.classList.add("on");
    } catch (err) {
      badge.textContent = "offline commands";
      badge.classList.remove("on");
    }
  }

  async function askChatService() {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60000);
    try {
      let response;
      try {
        response = await fetch(API_BASE + "/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: chat.history.slice(-10),
            context: chat.host.getContext()
          }),
          signal: controller.signal
        });
      } catch (err) {
        throw new Error("dashboard-offline");
      }
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || "chat service error");
      return data;
    } finally {
      clearTimeout(timer);
    }
  }

  /* Page-independent smalltalk + FAQ; everything else goes to the host,
     then the AI tier. Greetings run first so short messages never get
     fuzzy-matched into an action. */
  function parseGenericIntent(text) {
    const t = text.trim().toLowerCase().replace(/[""'']/g, "");
    if (!t) return null;
    if (/^(hi|hello|hey|yo|sup|good (morning|afternoon|evening))\b/.test(t))
      return { reply: "Hey! Tell me what to do, or ask “what can you do?”" };
    if (/^(thanks|thank you|thx|ty|nice|cool|great|awesome|perfect)\b/.test(t))
      return { reply: "Anytime. Say the word when you want the next one made." };
    if (/what can you do|^help$|^capabilities|what do you do|how do i use you/.test(t))
      return { reply: chat.host.capabilities };
    if (/(is|are)\s.*\b(video|render)s?\b.*\b(done|ready|finished)\b|render status|check (my )?(renders?|videos?)|any new videos|how('s| is) (the |my )?render(ing)?\b(?! work)|is it done/.test(t))
      return { action: { name: "check_renders", args: {} } };
    if (/\b(?:post kit|captions?|hashtags?)\b/.test(t) &&
        /\b(my|newest|latest|last|video)\b/.test(t) &&
        !/where|come from|how (do|does|are)/.test(t)) {
      const m = t.match(/\bfor\s+(?:the\s+|my\s+)?(.+?)(?:\s+video)?[?.!\s]*$/);
      return { action: { name: "get_post_kit", args: { video: m ? m[1] : "" } } };
    }
    if (/\b(?:mark|flag)\b.*\b(?:posted|uploaded|published)\b|^(?:i\s+)?(?:just\s+)?posted\s+(?:it|that|this)\b|\bun-?mark\b.*\bposted\b/.test(t)) {
      const posted = !/\bun-?mark|\bnot posted|didn'?t post/.test(t);
      const m = t.match(/\b(?:mark|flag)\s+(?:the\s+|my\s+)?(.+?)\s+(?:video\s+)?as\s+(?:posted|uploaded|published)/) ||
                t.match(/\b(?:mark|flag)\s+(?:the\s+|my\s+)?(.+?)\s+(?:posted|uploaded|published)/);
      return { action: { name: "mark_posted", args: { video: m ? m[1] : "", posted } } };
    }
    return null;
  }

  async function send(text) {
    if (chat.busy || !text.trim()) return;
    chat.busy = true;
    chat.ui.chips.hidden = true;
    addMsg("user", text);
    chat.history.push({ role: "user", content: text.slice(0, 1000) });
    const thinking = addMsg("bot", "…", true);

    let reply, copyPayload = null;
    // Actions usually return a status string; {text, copy} adds a copy button.
    const normalize = (r) => {
      if (r && typeof r === "object") { copyPayload = r.copy || null; return r.text; }
      return r;
    };
    try {
      const local = parseGenericIntent(text) || chat.host.parseIntent(text);
      if (local) {
        reply = local.reply || "";
        if (local.action) {
          thinking.textContent = "On it…";
          reply = normalize(await runAction(local.action)) || reply || "Done.";
        }
      } else {
        const kb = kbAnswer(text);
        if (kb) {
          reply = kb;
        } else {
          thinking.textContent = "Thinking…";
          const data = await askChatService();
          reply = String(data.reply || "").trim();
          if (data.action && data.action.name) {
            const result = normalize(await runAction(data.action));
            if (result) reply = reply ? `${reply}\n${result}` : result;
          }
          if (!reply) reply = "Done.";
        }
      }
    } catch (err) {
      reply = err && err.message === "dashboard-offline"
        ? "I can run commands and answer app questions offline, but for open-ended questions I need the Studio helper — double-click “Start-What-If-Studio” in the project folder once, then ask again."
        : "That request hiccuped — try again in a moment, or rephrase it as a command like “open …” or “go to …”.";
      ping();
    }
    thinking.remove();
    const node = addMsg("bot", reply);
    if (copyPayload) attachCopyButton(node, copyPayload);
    chat.history.push({ role: "assistant", content: reply.slice(0, 1000) });
    chat.busy = false;
    saveChatState();
  }

  function attachCopyButton(msgNode, payload) {
    const btn = build("button", "assistant-copy", "📋 Copy post kit");
    btn.type = "button";
    btn.addEventListener("click", () => {
      const done = (ok) => {
        btn.textContent = ok ? "✓ Copied" : "Copy failed — select the text above";
        setTimeout(() => { btn.textContent = "📋 Copy post kit"; }, 2000);
      };
      const fallback = () => {
        const area = document.createElement("textarea");
        area.value = payload;
        area.style.position = "fixed";
        area.style.left = "-9999px";
        document.body.appendChild(area);
        area.select();
        let ok = false;
        try { ok = document.execCommand("copy"); } catch (err) { ok = false; }
        document.body.removeChild(area);
        done(ok);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(payload).then(() => done(true), fallback);
      } else {
        fallback();
      }
    });
    msgNode.appendChild(btn);
    chat.ui.log.scrollTop = chat.ui.log.scrollHeight;
  }

  /* ---------- boot ---------- */

  function boot() {
    chat.host = window.assistantHost || makeDashboardHost();

    const style = document.createElement("style");
    style.textContent = CSS;
    document.head.appendChild(style);

    const fab = build("button", "assistant-fab", "✦");
    fab.type = "button";
    fab.setAttribute("aria-label", "Open the studio assistant");
    fab.setAttribute("aria-expanded", "false");

    const panel = build("section", "assistant-panel");
    panel.hidden = true;
    panel.setAttribute("aria-label", "Studio assistant");

    const head = build("div", "assistant-head");
    head.appendChild(build("span", "assistant-title", "✦ Studio Assistant"));
    const mode = build("span", "assistant-mode", "…");
    mode.title = "Commands and the FAQ always work offline. With the Studio helper running, free-form questions get AI answers too.";
    head.appendChild(mode);
    const close = build("button", "assistant-close", "✕");
    close.type = "button";
    close.setAttribute("aria-label", "Close assistant");
    head.appendChild(close);

    const log = build("div", "assistant-log");
    log.setAttribute("role", "log");
    log.setAttribute("aria-live", "polite");

    const chips = build("div", "assistant-chips");

    const form = build("form", "assistant-form");
    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = "Ask, or tell me what to do…";
    input.autocomplete = "off";
    input.setAttribute("aria-label", "Message the assistant");
    const sendBtn = build("button", "assistant-send", "Send");
    sendBtn.type = "submit";
    form.append(input, sendBtn);

    panel.append(head, log, chips, form);
    document.body.append(fab, panel);
    chat.ui = { fab, panel, log, chips, input, mode };

    const suggestions = chat.host.page === "studio"
      ? ["What can you do?", "Give me an idea", "Make a video about elevator music", "How does rendering work?"]
      : ["What can you do?", "How does rendering work?", "Go to studio", "Where do API keys go?"];

    const setOpen = (open, focus = true) => {
      panel.hidden = !open;
      fab.setAttribute("aria-expanded", String(open));
      if (open) {
        ping();
        if (!chat.greeted) {
          chat.greeted = true;
          addMsg("bot", "Hi — I'm your studio assistant. I know this whole app: I can answer questions, jump between pages, and on the Studio page open scenarios, change settings, and draft brand-new videos. What are we making?");
          suggestions.forEach(label => {
            const chip = build("button", "assistant-chip", label);
            chip.type = "button";
            chip.addEventListener("click", () => send(label));
            chips.appendChild(chip);
          });
        }
        if (focus) input.focus();
      } else if (focus) {
        fab.focus();
      }
      saveChatState(open);
    };

    fab.addEventListener("click", () => setOpen(panel.hidden));
    close.addEventListener("click", () => setOpen(false));
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !panel.hidden) setOpen(false);
    });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const text = input.value;
      input.value = "";
      send(text);
    });

    // Pick the conversation back up after navigating between pages.
    const saved = loadChatState();
    if (saved) {
      chat.greeted = Boolean(saved.greeted);
      chat.lastKitVideo = saved.lastKitVideo || null;
      chat.ui.chips.hidden = chat.greeted && (saved.history || []).length > 0;
      (saved.history || []).forEach(m => {
        if (m && typeof m.content === "string" && m.content) {
          chat.history.push({ role: m.role === "user" ? "user" : "assistant", content: m.content });
          addMsg(m.role === "user" ? "user" : "bot", m.content);
        }
      });
      if (saved.open) setOpen(true, false);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

})();
