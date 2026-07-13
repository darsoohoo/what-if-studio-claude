/* ============================================================
   What If Studio — app.js
   Static, local-only scenario engine for short-form content.
   No server, no accounts, no tracking, no remote dependencies.
   Runs directly from file:// — localStorage falls back to an
   in-memory store when the browser blocks it.
   ============================================================ */

"use strict";

/* ============================================================
   1. CONSTANTS
   ============================================================ */

const CATEGORIES = [
  "Speculative",
  "Science",
  "History",
  "Pop Culture",
  "Internet Mystery",
  "Alternate Reality",
  "Unsettling Everyday",
  "Scary/Weird",
  "Scary Story",
  "True History"
];

/* Default card colors for custom scenarios, per category. */
const CATEGORY_COLORS = {
  "Speculative": ["#2dbf8b", "#3a6ea5"],
  "Science": ["#3b4368", "#6a5ae0"],
  "History": ["#b8a13a", "#b8563a"],
  "Pop Culture": ["#b83a6e", "#6a5ae0"],
  "Internet Mystery": ["#2d8a6e", "#151a30"],
  "Alternate Reality": ["#6a5ae0", "#2d8a6e"],
  "Unsettling Everyday": ["#3b4368", "#2dbf8b"],
  "Scary/Weird": ["#151a30", "#b83a6e"],
  "Scary Story": ["#120a16", "#8a2431"],
  "True History": ["#3d2f1a", "#8a6d2f"]
};

/* One package works everywhere: the spoken outro uses a platform-neutral CTA,
   and per-platform hashtags come from the render's post kit, not the package.
   Story categories carry their own follow line (the render's burned-in CTA
   card and anchor hashtag follow the category too — see pipeline). */
const NEUTRAL_CTA = "Follow for the next what-if.";
const CATEGORY_CTA = {
  "Scary Story": "Follow for more scary stories.",
  "True History": "Follow for more true history."
};
const HYPE_LEAD = {
  "Scary Story": "That's the story — tell me what you'd have done.",
  "True History": "That's the true story — tell me which part you didn't believe."
};
const ASPECT = "9:16 vertical";

const RUNTIMES = [
  { id: 30, label: "30s", beats: 3, note: "Tight cut: hook, three fast beats, out. Every word earns its place." },
  { id: 60, label: "60s", beats: 5, note: "Standard cut: full beat structure at a brisk pace." },
  { id: 90, label: "90s", beats: 5, note: "Room to breathe: full beat structure with one extra detail or example per beat — let the twist land (~15s per beat)." },
  { id: 180, label: "3 min", beats: 5, note: "Extended cut: expand each beat with one extra example, visual, or aside (~25–30s per beat)." }
];

const VOICES = [
  { id: "calm", label: "Calm Narrator", direction: "Low, steady, confident. Let pauses do the scaring. Never rush the payoff line." },
  { id: "hype", label: "High-Energy Storyteller", direction: "Fast, punchy, incredulous. Hit every twist like breaking news. Big emphasis on numbers." },
  { id: "deadpan", label: "Deadpan Documentarian", direction: "Flat, dry, matter-of-fact. Deliver the wildest lines like a weather report. Comedy lives in the contrast." }
];


const STORAGE_KEY = "whatIfStudio.v1";

/* ============================================================
   2. SCENARIO BANK — 37 scenarios across 10 categories
   ============================================================ */

const scenarioBank = [

  /* ---------------- SPECULATIVE ---------------- */
  {
    id: "sp-jump",
    category: "Speculative",
    title: "What if all 8 billion people jumped at once?",
    image: { glyph: "🌍", from: "#4a7bd4", to: "#2dbf8b" },
    premise: "Every human on Earth gathers in one place and jumps at the exact same second. The physics answer is funnier — and stranger — than the disaster you're imagining.",
    tags: ["physics", "earth", "numbers", "thought experiment"],
    safety: "Fictional thought experiment — uses real physics estimates to describe an impossible event.",
    hooks: [
      "8 billion people. One jump. Here's what actually happens.",
      "Scientists actually calculated this — and the answer is embarrassing.",
      "It wouldn't be the jump that gets us. It's what happens after everyone lands."
    ],
    beats: [
      "Cold open: everyone on Earth crammed into an area about the size of Los Angeles — that's step one, and it's already the weirdest part.",
      "The jump itself: 8 billion bodies push the Earth roughly a hundredth of the width of a single atom. The planet does not care.",
      "The landing: a synchronized thud comparable to a moderate earthquake near the crowd — locally scary, globally nothing.",
      "The real catastrophe: 8 billion people now stuck in one city with no food, water, or bathrooms. The jump was fine; the crowd is the apocalypse.",
      "Payoff: the Earth wins this fight without noticing it was in one. The scariest force wasn't gravity — it was logistics."
    ],
    shotList: [
      "Hook shot: rapid zoom on a world map collapsing all population dots into one glowing point.",
      "Overhead crowd loop with a giant \"3…2…1…\" countdown overlay.",
      "Side-view sketch: stick-figure crowd jumps, planet wobbles a comically tiny amount with an \"actual scale\" caption.",
      "Seismograph graphic spiking then flatlining, split-screen labeled \"local vs global\".",
      "Slow push-in on the packed-city map while the logistics twist lands.",
      "End card: \"What should everyone do at the same time next?\" comment prompt."
    ],
    captions: [
      "8 billion people jump at once — physics says the Earth barely flinches 🌍",
      "The jump isn't the problem. The landing isn't either. It's what comes after.",
      "We did the math on humanity's biggest jump scare."
    ],
    thumbnails: [
      "8,000,000,000 JUMP",
      "Earth vs Everyone",
      "The jump heard by no one"
    ]
  },
  {
    id: "sp-money",
    category: "Speculative",
    title: "What if money expired after 30 days?",
    image: { glyph: "💸", from: "#2dbf8b", to: "#b8a13a" },
    premise: "Every dollar you earn deletes itself in 30 days unless you spend it. Saving is impossible. Economists have actually flirted with this idea — and it gets weird fast.",
    tags: ["economics", "society", "money", "thought experiment"],
    safety: "Speculative fiction with a real-economics footnote (demurrage currency). Not financial advice.",
    hooks: [
      "Your paycheck now self-destructs in 30 days. What do you do first?",
      "A world with no savings accounts — and it almost happened for real.",
      "Expiring money sounds insane. One town actually tried it — and it worked too well."
    ],
    beats: [
      "The rule: every unit of money evaporates 30 days after you receive it. No savings, no hoarding, no \"someday\".",
      "Week one: everyone spends like it's the end of the world — because for their wallet, it is. The economy enters permanent Black Friday.",
      "The adaptation: people stop storing money and start storing things — tools, skills, favors, land. Wealth becomes whatever doesn't expire.",
      "The twist: a real version existed — in the 1930s the town of Wörgl, Austria issued expiring money during the Depression, and local business boomed until authorities shut it down.",
      "Payoff: money is frozen time. Put an expiration date on it, and you find out what people actually value."
    ],
    shotList: [
      "Hook: cash dissolving pixel-by-pixel under a 30-day countdown timer.",
      "Fast montage: shopping rush, empty bank vault, dusty \"SAVINGS\" sign.",
      "Whiteboard sketch: money arrows redirecting into tools, skills, land.",
      "Old-photo treatment of Wörgl with a \"this really happened\" stamp.",
      "Direct-to-camera closer: \"so what would YOU buy on day 29?\""
    ],
    captions: [
      "POV: your money deletes itself in 30 days 💸",
      "No savings. No hoarding. One town actually tried this.",
      "Expiring money — dumbest idea ever, or a reset button?"
    ],
    thumbnails: [
      "MONEY: 30 DAYS LEFT",
      "The cash that deletes itself",
      "Savings = IMPOSSIBLE"
    ]
  },
  {
    id: "sp-photosynthesis",
    category: "Speculative",
    title: "What if humans could photosynthesize?",
    image: { glyph: "🌿", from: "#3fae62", to: "#a4c93d" },
    premise: "Your skin works like a leaf: stand in the sun, make sugar. Sounds like free lunch — until you do the math on how much surface area a person actually has.",
    tags: ["biology", "evolution", "sun", "thought experiment"],
    safety: "Fictional biology scenario — real photosynthesis math, imaginary humans.",
    hooks: [
      "Green skin, free food, no groceries — there's just one fatal math problem.",
      "If humans photosynthesized, lunch would take all day. Standing still. In full sun.",
      "Plants figured out free food. Here's why you never will."
    ],
    beats: [
      "The dream: green-skinned humans soaking up sunlight instead of buying groceries. Hunger solved, right?",
      "The math: a leaf only has to feed a leaf. Human skin is about two square meters — enough sunlight for maybe a sandwich's worth of energy per day, if you sunbathe from dawn to dusk.",
      "The redesign: to actually live on light you'd need skin flaps like solar sails — humans become slow, flat, tree-shaped things that can't afford to move.",
      "The trade: plants pay for free food by standing still forever. Movement is expensive — that's why animals eat instead of basking.",
      "Payoff: you don't have chlorophyll because your ancestors picked a different superpower — running away. Food is the price of motion."
    ],
    shotList: [
      "Hook: green-tinted filter snapping onto a portrait, sun flare behind.",
      "Napkin-math overlay: skin area vs leaf area, \"1 sandwich/day\" stamp.",
      "Absurd sketch: human with giant leaf-wings tipping over mid-step.",
      "Split screen: cheetah sprinting vs tree standing, labeled \"two business models\".",
      "Closer: narrator takes a bite of an actual sandwich. \"Worth it.\""
    ],
    captions: [
      "Free food from sunlight? The math says: one sad sandwich a day 🌿",
      "Why you don't photosynthesize (and why that's a flex)",
      "Plants unlocked free food. The fee: never moving again."
    ],
    thumbnails: [
      "HUMAN = PLANT?",
      "Free food glitch ❌",
      "1 sandwich per day"
    ]
  },

  /* ---------------- SCIENCE ---------------- */
  {
    id: "sc-moon",
    category: "Science",
    title: "What if the Moon disappeared tonight?",
    image: { glyph: "🌑", from: "#3b4368", to: "#151a30" },
    premise: "At midnight the Moon silently blinks out of existence. The first week is eerie. The next thousand years quietly unravel the planet.",
    tags: ["space", "astronomy", "earth", "disaster"],
    safety: "Impossible hypothetical used to explain real lunar science — not a prediction.",
    hooks: [
      "If the Moon vanished at midnight, you wouldn't notice until the oceans did.",
      "The Moon isn't decoration. It's Earth's stabilizer — and here's what breaks without it.",
      "No explosion. No warning. Just… no Moon. Day one is fine. Year 1,000 is not."
    ],
    beats: [
      "Minute one: no crash, no flash — the night just gets darker, and every owl on Earth has the best hunting night of its life.",
      "Day two: tides shrink to roughly a third of their size (the Sun still pulls some). Coastal ecosystems that run on tidal rhythm start missing their heartbeat.",
      "Year ten: pitch-black nights. Moonlight navigation is gone for millions of animals — sea turtles, corals, moths all take the hit.",
      "Millennium: without the Moon steadying Earth's tilt, the axis slowly begins to wander — over millions of years, seasons drift toward chaos.",
      "Payoff: the Moon isn't a nightlight. It's a flywheel keeping Earth's climate story boring — and boring is what let life get complicated."
    ],
    shotList: [
      "Hook: timelapse night sky; the Moon hard-cuts to empty black with a soft \"pop\".",
      "Beach shot with animated tide lines shrinking, \"-66%\" overlay.",
      "Dark montage: turtle hatchlings, moths, coral — each with a small \"signal lost\" glitch.",
      "Spinning-top animation: steady spin vs wobbling top, labeled \"Earth's tilt\".",
      "Slow zoom on the Moon for the closer line, then cut to black."
    ],
    captions: [
      "The Moon vanished at midnight. Day 1 is fine. Year 1,000 isn't. 🌑",
      "Turns out the Moon has a job.",
      "What the Moon quietly does for you every single night."
    ],
    thumbnails: [
      "MOON: DELETED",
      "Night one without the Moon",
      "Earth's missing flywheel"
    ]
  },
  {
    id: "sc-blackhole",
    category: "Science",
    title: "What if you fell into a black hole?",
    image: { glyph: "🕳️", from: "#151a30", to: "#6a5ae0" },
    premise: "You dive feet-first into a black hole. Depending on which one you picked, you're either shredded into atoms or you cross the point of no return without feeling a thing — and both answers are stranger than sci-fi.",
    tags: ["space", "physics", "black holes", "extreme"],
    safety: "Real physics, imaginary traveler — nobody is harmed in a thought experiment.",
    hooks: [
      "Falling into a black hole feet-first? Your feet arrive first. That's the problem.",
      "Pick your black hole carefully — one shreds you instantly, one just… keeps you.",
      "There's a version of this where you cross the event horizon and feel absolutely nothing."
    ],
    beats: [
      "Setup: two doors — a small black hole and a supermassive one. How this goes depends entirely on which you pick.",
      "The small one: gravity at your feet is so much stronger than at your head that you're stretched into a strand of atoms. Physicists genuinely call it spaghettification.",
      "The big one: at a supermassive black hole the horizon is so far from the center that you cross it without a bump. No alarm. No wall. You just can't come back.",
      "The weird part: a friend watching from outside never sees you fall in — your image freezes at the horizon and slowly fades to black, while you keep falling.",
      "Payoff: two true stories at once — you fell in; they watched you freeze forever. Both correct. That's relativity, and nobody finds it comfortable."
    ],
    shotList: [
      "Hook: two glowing doors graphic with a flickering \"CHOOSE\".",
      "Stretching-noodle animation of a stick figure, \"spaghettification\" typed on screen.",
      "Smooth first-person dolly through a dark ring — no impact, heartbeat audio only.",
      "Split screen: falling POV vs the outside observer's frozen, fading image.",
      "End on a black frame, single line of white text: \"still falling.\""
    ],
    captions: [
      "Feet-first into a black hole — a physics horror story 🕳️",
      "One black hole shreds you. The other just… keeps you.",
      "The universe's only one-way door, explained in 60 seconds."
    ],
    thumbnails: [
      "PICK A BLACK HOLE",
      "Still falling…",
      "The one-way door"
    ]
  },
  {
    id: "sc-antibiotics",
    category: "Science",
    title: "What if antibiotics stopped working tomorrow?",
    image: { glyph: "🧫", from: "#b8563a", to: "#3b4368" },
    premise: "Overnight, every antibiotic becomes useless. Modern medicine doesn't collapse where you'd expect — it collapses everywhere else first: surgery, dentistry, transplants, chemo.",
    tags: ["medicine", "biology", "society", "real risk"],
    safety: "Dramatized hypothetical grounded in a real public-health topic (antibiotic resistance). Keep tone informative, avoid panic framing, and never give medical advice.",
    hooks: [
      "The scariest what-if on this channel is the one scientists say is slowly happening.",
      "No antibiotics tomorrow — and suddenly a paper cut is a story your family tells carefully.",
      "Surgery, dentists, chemo — none of it works without one 1928 accident."
    ],
    beats: [
      "Setup: it's not a monster scenario — it's an eraser. One shelf of medicine goes blank, and ninety years of confidence goes with it.",
      "First domino: routine surgery becomes high-stakes again — the real trick of surgery was never the cutting, it was keeping the wound clean after.",
      "Hidden dominoes: dental work, C-sections, chemotherapy, transplants — all of them quietly lean on antibiotics like a load-bearing wall.",
      "The real-world hook: this is the slow-motion version of a real issue — antibiotic resistance grows every year, which is why doctors guard these drugs like a vault.",
      "Payoff: the age of medical miracles started with mold on a forgotten dish in 1928. This what-if isn't fiction — it's a countdown we can still slow down."
    ],
    shotList: [
      "Hook: pharmacy shelf timelapse with one row of boxes fading to grey.",
      "Operating-room stock footage; the music drops out on the \"clean wound\" line.",
      "Icon cascade: tooth, stork, IV bag, heart — each dimming in turn.",
      "Marker-style line graph rising, labeled \"resistance\".",
      "Archival-style petri dish shot, warm light, closer line delivered over it."
    ],
    captions: [
      "The what-if that's quietly real: a world where antibiotics fail 🧫",
      "Modern medicine is a tower. This is the block at the bottom.",
      "Why doctors treat antibiotics like a vault, not a vending machine."
    ],
    thumbnails: [
      "MEDICINE'S OFF SWITCH",
      "The 1928 miracle expires",
      "One shelf goes blank"
    ]
  },

  /* ---------------- HISTORY ---------------- */
  {
    id: "hi-alexandria",
    category: "History",
    title: "What if the Library of Alexandria never burned?",
    image: { glyph: "📜", from: "#b8a13a", to: "#b8563a" },
    premise: "History's most famous lost-knowledge story gets rewritten: the Library survives every fire, every war, every budget cut. Do we get starships by the year 900 — or is the truth more deflating?",
    tags: ["history", "knowledge", "ancient world", "alternate history"],
    safety: "Alternate history — clearly framed speculation layered on debated historical events.",
    hooks: [
      "\"We'd have starships by now\" — the internet's favorite history myth, put to the test.",
      "The Library of Alexandria didn't die the way you think it did.",
      "Save one building in 48 BC and maybe you skip the Dark Ages… or maybe nothing changes."
    ],
    beats: [
      "The legend: one fire, all ancient knowledge gone, humanity set back a thousand years. Perfect story. Mostly wrong.",
      "The correction: the Library declined over centuries — budget cuts, political purges, neglect. It wasn't murdered; it was defunded to death.",
      "The rewrite: so our what-if has to save it differently — imagine Alexandria funded forever, a permanent engine of copied, translated, argued-over texts.",
      "The honest outcome: most of what was lost was literature and philosophy, not schematics. No warp drives — but maybe the scientific method arrives centuries early, and that changes everything downstream.",
      "Payoff: the real lesson survived the fire — knowledge doesn't die in flames; it dies when nobody pays the librarians."
    ],
    shotList: [
      "Hook: dramatic burning-scroll shot that freezes mid-flame with a record scratch.",
      "Ledger-style graphic: a \"funding\" line declining across centuries.",
      "Warm montage: hands copying scrolls, candlelight, shelves multiplying.",
      "Split timeline: \"our 1600s\" vs \"their 900s\" with a scientific-method icon jumping tracks.",
      "Quiet closer: a modern library at dusk, lights turning off shelf by shelf."
    ],
    captions: [
      "The Library of Alexandria myth vs what actually happened 📜",
      "Saving one library ≠ starships. The real answer is better.",
      "Knowledge doesn't burn. It gets defunded."
    ],
    thumbnails: [
      "THE FIRE IS A LIE",
      "Starships by 900 AD?",
      "Who really killed the Library"
    ]
  },
  {
    id: "hi-blackdeath",
    category: "History",
    title: "What if the Black Death never happened?",
    image: { glyph: "🏰", from: "#5a4a7a", to: "#3b4368" },
    premise: "The plague that killed a third of Europe never arrives. Millions live — and, in one of history's ugliest ironies, the modern world might arrive centuries late.",
    tags: ["history", "medieval", "pandemic", "alternate history"],
    safety: "Sensitive historical topic — the deaths were real. Keep tone factual and respectful; the hypothetical removes a tragedy, it never celebrates one.",
    hooks: [
      "History's darkest century might have accidentally built your world.",
      "No Black Death = no Renaissance? The uncomfortable math of 1348.",
      "What if the worst thing in history never happened? Careful what you wish for."
    ],
    beats: [
      "The change: 1347 — the plague ships never dock. The third of Europe that died now lives. On its face, a pure win.",
      "The catch: after the real plague, labor was suddenly scarce — surviving peasants could demand wages, and serfdom cracked. Remove the plague, and that leverage never appears.",
      "The slow world: cheap labor forever means less pressure to invent, weaker cities, a longer feudal age. The engine that pushed toward the Renaissance idles.",
      "The honest caveat: history isn't a machine — change might arrive another way, later and gentler. But many historians agree the shock accelerated the old world's collapse.",
      "Payoff: nobody should wish for catastrophe. The unsettling truth is just that our comfortable timeline was partly built by an uninvited one."
    ],
    shotList: [
      "Hook: medieval map with a plague-spread animation that rewinds to zero.",
      "Field-work montage with a wage ledger appearing, numbers climbing.",
      "Slow-motion gears labeled \"invention pressure\" winding down.",
      "Historian's desk: two timeline cards side by side, a hand hovering between them.",
      "Closer: a single candle in a dark room; the final line; the candle stays lit."
    ],
    captions: [
      "The plague ships never dock. History holds its breath. 🏰",
      "The uncomfortable link between 1348 and your modern life.",
      "Alternate history where the tragedy never happens — and the future runs late."
    ],
    thumbnails: [
      "1348: CANCELED",
      "The plague that built modernity?",
      "A kinder, slower world"
    ]
  },
  {
    id: "hi-napoleon",
    category: "History",
    title: "What if Napoleon had escaped to America?",
    image: { glyph: "⛵", from: "#3a6ea5", to: "#b8a13a" },
    premise: "1815, after Waterloo: instead of surrendering, Napoleon boards a ship for the United States — a real plan his allies actually prepared. What does the ex-emperor of Europe do in New Jersey?",
    tags: ["history", "napoleon", "america", "alternate history"],
    safety: "Playful alternate history built on a documented real escape plan — label the speculation clearly.",
    hooks: [
      "Napoleon almost moved to America. There was a boat. There was a plan. He said no.",
      "The emperor of Europe, retired, in New Jersey. This nearly happened.",
      "History's most famous conqueror had a Plan B: become an American celebrity."
    ],
    beats: [
      "The real setup: after Waterloo, Napoleon's circle genuinely organized an American escape — ships at Rochefort, supporters in Philadelphia. His own brother Joseph made it there and lived like a star.",
      "The divergence: this time he boards. Weeks dodging the Royal Navy, then an American harbor — the most famous man alive walks down a gangplank with no army.",
      "The awkward middle: America is fascinated and nervous. He's a dinner guest, a tourist attraction, a diplomatic headache — a lion in a petting zoo.",
      "The temptation: veterans drift toward him; whispers about Spanish territories and Mexico. Does the eagle stay retired? His health was already failing — the comeback is probably a fantasy.",
      "Payoff: instead of a martyr fading on a rock in the Atlantic, we get memoirs, feuds, and portraits from a garden in New Jersey. A smaller ending — and a stranger world."
    ],
    shotList: [
      "Hook: classic Napoleon portrait with a suitcase edited in; hard zoom.",
      "Map animation: dotted escape route Rochefort → New York, patrol ships prowling.",
      "Period illustrations with modern captions (\"celebrity houseguest\").",
      "Dark map of the Americas, faint eagle silhouette over Mexico, whispered \"what if…\".",
      "Closer: quiet garden scene, a quill on paper — \"a smaller ending, a stranger world.\""
    ],
    captions: [
      "Napoleon's real Plan B: America. He was one 'yes' away. ⛵",
      "The retirement arc history almost gave us.",
      "Emperor → immigrant. The wildest what-if of 1815."
    ],
    thumbnails: [
      "NAPOLEON IN AMERICA",
      "The escape boat was real",
      "Emperor next door"
    ]
  },

  /* ---------------- POP CULTURE ---------------- */
  {
    id: "pc-beatles",
    category: "Pop Culture",
    title: "What if the Beatles never broke up?",
    image: { glyph: "🎸", from: "#b83a6e", to: "#6a5ae0" },
    premise: "1970: instead of splitting, the Beatles negotiate a truce — solo albums allowed, a band album every two years. Music's biggest what-if gets a realistic playthrough, not a fairy tale.",
    tags: ["music", "beatles", "bands", "alternate history"],
    safety: "Speculation about public figures' public careers — keep it respectful; handle real-world tragedy (1980) with care.",
    hooks: [
      "The arrangement that could've saved the Beatles is one every band uses now.",
      "The 70s with a new Beatles album every two years — better music, or a slow fade?",
      "The breakup made them immortal. The reunion timeline has to pay for more music with the myth."
    ],
    beats: [
      "The fix: the real poison was business and burnout, not hatred — so the deal is simple: full solo freedom, a band album every couple of years. Bands do this constantly today.",
      "Album one, 1972: the solo songs we know get filtered back through the band — arguably the greatest album ever assembled… or four solo acts sharing a cover. Fans would argue forever.",
      "The friction: without the breakup wound, do they write the same songs? Some of that solo fire WAS the divorce. A truce might soften the art.",
      "The long game: by the 80s they're an institution — stadium reunions, a live-TV moment that stops the world. And the darkest fork in the timeline: in a world where John's daily life moved differently, does December 1980 still happen at all?",
      "Payoff: the breakup froze them at their peak, forever perfect. The reunion timeline trades the myth for more music. Which would you actually choose?"
    ],
    shotList: [
      "Hook: a contract sliding across a table, four signatures animating on.",
      "Mock album grid: real solo-era covers merging into one imagined 1972 cover.",
      "Era-graded interview-style split screens through the decades.",
      "Stadium crowd footage with an \"1985\" chyron, 80s color grade.",
      "Closer: a vinyl record spinning down to a stop; the question lands over the run-out groove."
    ],
    captions: [
      "The deal that could've saved the Beatles was… completely normal? 🎸",
      "1972's imaginary Beatles album is stacked.",
      "Perfect myth vs more music — pick a timeline."
    ],
    thumbnails: [
      "THE TRUCE OF 1970",
      "One more album",
      "Beatles: the reunion era"
    ]
  },
  {
    id: "pc-blockbuster",
    category: "Pop Culture",
    title: "What if Blockbuster had bought Netflix?",
    image: { glyph: "📼", from: "#3a6ea5", to: "#b8563a" },
    premise: "In 2000, Netflix offered itself to Blockbuster for $50 million. Blockbuster passed. In this timeline they say yes — and the future of streaming belongs to a video store.",
    tags: ["tech", "business", "streaming", "alternate history"],
    safety: "Real business history plus clearly labeled speculation — never present the alternate outcome as certain.",
    hooks: [
      "Netflix offered itself to Blockbuster for $50M. The room reportedly held back laughter.",
      "One meeting in 2000 decided who owns your Friday nights.",
      "In another timeline, you're paying a Blockbuster subscription right now."
    ],
    beats: [
      "The real meeting: 2000, dot-com crash, Netflix bleeding cash, offering itself for $50 million. Blockbuster passes. That part is true.",
      "The divergence: Blockbuster says yes — but here's the trap: buying Netflix doesn't make you Netflix. Big companies usually buy disruptors and then quietly smother them to protect the old business.",
      "The knife edge: late fees were a giant revenue line — streaming kills late fees. Would any executive burn their best cash machine to feed a $50M side project?",
      "The honest fork: most likely, Blockbuster-Netflix dies in a corporate drawer — and someone else invents streaming a few years later anyway. The idea was coming; only the logo was negotiable.",
      "Payoff: the lesson isn't \"Blockbuster was dumb.\" It's that the future usually gets built by someone with nothing to lose. Disruption is rarely bought — it's escaped."
    ],
    shotList: [
      "Hook: reenacted boardroom freeze-frame with a \"$50,000,000\" stamp.",
      "Split screen: bustling Blockbuster store vs a tiny Netflix office, year-2000 grade.",
      "Bar graphic: \"late fee revenue\" towering over \"Netflix asking price\".",
      "A drawer sliding shut over a red logo; dust motes; muffled audio.",
      "Closer: empty video-store storefront at night, one light flickering."
    ],
    captions: [
      "The $50M 'no' that built Netflix 📼",
      "Blockbuster didn't lose to Netflix. It lost to its own favorite revenue line.",
      "Would streaming even exist if Blockbuster said yes?"
    ],
    thumbnails: [
      "THE $50M MISTAKE",
      "Blockbuster+ (2004)",
      "One meeting. Two futures."
    ]
  },
  {
    id: "pc-endings",
    category: "Pop Culture",
    title: "What if the internet voted on movie endings?",
    image: { glyph: "🎬", from: "#6a5ae0", to: "#b83a6e" },
    premise: "Every big movie now ships with a live final-act vote. Opening night, forty million phones decide who lives. Hollywood's writers are — obviously — thrilled.",
    tags: ["movies", "internet", "hollywood", "satire"],
    safety: "Original satirical premise — commentary on fan culture, not leaks or claims about real films.",
    hooks: [
      "Opening night. Final scene. Forty million phones get to choose who dies.",
      "Democracy comes for movie night — a thought experiment.",
      "The ending you watched isn't the ending they wrote. The internet outvoted them."
    ],
    beats: [
      "The rule: every blockbuster's last ten minutes exist in three versions. The audience votes live. Majority rules — everywhere, forever.",
      "Month one: pure chaos-joy — villains get redemption arcs because they're popular, beloved dogs become unkillable, and one meme campaign promotes a side character to lead.",
      "The corruption: studios learn to rig the menu — no studio will risk a sad ending again, so all three \"choices\" become the same safe ending wearing different hats.",
      "The rebellion: writers start hiding their real endings in the losing options, and film fans form voting blocs to save them. Art becomes an election, complete with campaign ads.",
      "Payoff: it turns out the ending was never the product — the argument about the ending is. And we already live in that world. The vote would just make it official."
    ],
    shotList: [
      "Hook: cinema screen with a giant voting overlay, countdown clock, phones glowing in the dark.",
      "Meme-speed montage: fake headlines, fan-cam edits, a \"SAVE THE DOG 🐶\" trending graphic.",
      "Three doors graphic merging into one identical door; a studio logo winks.",
      "Parody \"campaign ad\" for an ending, with tiny disclaimer text scrolling.",
      "Closer: two friends arguing outside the cinema as the camera pulls away."
    ],
    captions: [
      "40 million phones vs one screenwriter 🎬",
      "Choose-your-own-ending cinema: utopia or menace?",
      "The internet would never let a sad ending survive. Discuss."
    ],
    thumbnails: [
      "VOTE TO SAVE HIM",
      "Endings: now a poll",
      "Hollywood vs the group chat"
    ]
  },

  /* ---------------- INTERNET MYSTERY ---------------- */
  {
    id: "im-cicada",
    category: "Internet Mystery",
    title: "What if Cicada 3301 never stopped recruiting?",
    image: { glyph: "🧩", from: "#2d8a6e", to: "#151a30" },
    premise: "The internet's most elegant puzzle went publicly quiet in 2014. This scenario asks the question every solver quietly believes: what if the game never ended — it just stopped announcing itself?",
    tags: ["internet", "puzzles", "mystery", "cicada 3301"],
    safety: "Real unsolved mystery — keep documented facts clearly separated from speculation; never claim to identify members or answers.",
    hooks: [
      "The internet's hardest puzzle didn't end in 2014. It just stopped saying 'start'.",
      "Thousands tried. A handful went quiet. Then the puzzle itself went quiet.",
      "What if the world's strangest recruitment test is running right now — and round one is simply noticing it?"
    ],
    beats: [
      "The facts first: from 2012 to 2014, an anonymous group posted puzzles chaining cryptography, obscure literature, and real-world clues across the globe. Winners were contacted privately. Then: public silence. All documented.",
      "The pattern: the finalists who reportedly made it through went quiet too. Whatever was on the other side of the last door, nobody came back to describe it.",
      "The scenario: imagine the public puzzles were just the loudest round — and the real test continues in places you wouldn't think to look. A typo that isn't a typo. A dataset with one strange row.",
      "The chill: in this version the puzzle isn't hidden from you — it's hidden around you. And the first filter is brutal in its simplicity: do you notice anything at all?",
      "Payoff: we frame this as fiction because we have to. But the documented record genuinely ends mid-sentence — and stories that end mid-sentence never really end."
    ],
    shotList: [
      "Hook: the cicada emblem glitching onto everyday images — receipts, signage, static.",
      "Archive montage of the public puzzle era with a timeline bar: 2012 → 2014 → \"?\".",
      "Dark forum-thread mockup, usernames fading to grey one by one.",
      "Slow pan across a mundane desk where one item subtly repeats the emblem.",
      "Closer: black screen, a single blinking cursor, no text. Let it sit."
    ],
    captions: [
      "The puzzle stopped announcing itself. That's not the same as stopping. 🧩",
      "Cicada 3301: the documented record ends mid-sentence.",
      "What if round one is just… noticing?"
    ],
    thumbnails: [
      "STILL RECRUITING?",
      "The last door",
      "3301 NEVER LEFT"
    ]
  },
  {
    id: "im-website",
    category: "Internet Mystery",
    title: "What if a website you remember never existed?",
    image: { glyph: "🕸️", from: "#5a4a7a", to: "#2d8a6e" },
    premise: "You'd swear it was real: a game site, a forum, a weird little page from your childhood. No archive, no screenshots, nobody else remembers — or worse, thousands do. The internet's strangest category: lost media that may never have been found because it was never there.",
    tags: ["internet", "lost media", "memory", "mystery"],
    safety: "Memory-science framing — present false/collective memory as the grounded explanation; anything beyond it is labeled fiction.",
    hooks: [
      "Thousands of people remember this website. There's no evidence it ever existed.",
      "The Wayback Machine has hundreds of billions of pages. It doesn't have the one you remember.",
      "Lost media hunters have a category they hate: media that was never real."
    ],
    beats: [
      "The setup: lost-media forums are full of them — a flash game, a creepy kids' site, a forum that vanished. Detailed memories. Multiple witnesses. Zero archives.",
      "The reasonable answer: memory is a wiki that anyone can edit — childhood websites blur together, and one person's vivid description quietly installs itself into other people's pasts.",
      "The wrinkle: sometimes the search creates the thing — communities reconstruct the \"lost\" site from shared memory until a playable version exists… of something that may never have existed.",
      "The scenario: so here's the what-if — you finally find it. Exact URL, exact layout, every detail right. One problem: the page's own records say it was created last Tuesday.",
      "Payoff: the internet promised everything would be saved forever. Instead it built the perfect machine for making memories unverifiable — and that's the real mystery."
    ],
    shotList: [
      "Hook: retro browser window loading… then 404, with VHS-style degradation.",
      "Forum mockup: a \"does anyone else remember…\" thread, reply counter spinning up.",
      "Diagram: a memory 'wiki' being edited, one false detail propagating between heads.",
      "Reconstruction montage: a pixel site being rebuilt, then a timestamp: \"created: Tuesday\".",
      "Closer: cursor hovering over the rebuilt site's link. It doesn't click."
    ],
    captions: [
      "No archive. No screenshots. Thousands of witnesses. 🕸️",
      "The internet's strangest category: media that was never real.",
      "Your childhood website might be a group project your memory joined."
    ],
    thumbnails: [
      "IT WAS NEVER REAL",
      "404: your memory",
      "The site nobody can find"
    ]
  },
  {
    id: "im-solved",
    category: "Internet Mystery",
    title: "What if the internet's biggest mystery was already solved?",
    image: { glyph: "🔍", from: "#151a30", to: "#b8a13a" },
    premise: "Every famous unsolved internet mystery has thousands of people still digging. This scenario proposes something quietly maddening: one of them was solved years ago — and the person who solved it looked at the answer and chose silence.",
    tags: ["internet", "mystery", "secrets", "community"],
    safety: "Original speculative frame — all 'solvers' are fictional; no real person is identified or accused of anything.",
    hooks: [
      "Somewhere out there is a person who solved it — and said nothing.",
      "The worst ending for a mystery isn't 'unsolved'. It's 'solved, privately'.",
      "What if the rabbit hole you're in has a bottom — and someone is already standing on it?"
    ],
    beats: [
      "The setup: pick any legendary unsolved thing — a cipher, a vanished uploader, an unexplained broadcast. Communities orbit it for decades. The orbit becomes a culture.",
      "The scenario: one night, years ago, an ordinary person cracked it. Not a genius — just the right hobby, the right archive, the right coincidence.",
      "The choice: and the answer was… small. Mundane. The kind of explanation that kills the magic and dissolves a community they loved. So they closed the laptop.",
      "The ripple: they still visit the forums. They watch new theories bloom, each one wrong in a way only they can see. Is that kindness — or the loneliest hobby on Earth?",
      "Payoff: every great mystery has two endings — the answer, and the silence around it. You can't know which one you're living in. That's the real puzzle."
    ],
    shotList: [
      "Hook: rabbit-hole zoom through nested forum tabs, sudden stop in a dark room.",
      "Desk scene: screen glow on a face — the 'solve' moment, played with no music.",
      "The choice: cursor hovering over 'post reply'… then the laptop closing. Audio: just the click.",
      "Forum time-lapse: years of threads scrolling past one silent lurker's username.",
      "Closer: direct to camera — \"would you post it?\" — hold, cut to black."
    ],
    captions: [
      "Solved, privately. The cruelest ending a mystery can have. 🔍",
      "Somebody might already know. Sit with that.",
      "Would you kill the magic? Be honest."
    ],
    thumbnails: [
      "SOLVED. SILENT.",
      "The bottom of the rabbit hole",
      "They chose silence"
    ]
  },

  /* ---------------- ALTERNATE REALITY ---------------- */
  {
    id: "ar-1999",
    category: "Alternate Reality",
    title: "What if you woke up in 1999 with your phone?",
    image: { glyph: "📟", from: "#3a6ea5", to: "#5a4a7a" },
    premise: "You wake up on a Tuesday in 1999 with nothing but the clothes you slept in and a fully charged phone with no signal. It's the most powerful object on Earth — and it's mostly useless.",
    tags: ["time travel", "tech", "90s", "thought experiment"],
    safety: "Time-travel fiction — any get-rich-quick angles are part of the fiction, not advice.",
    hooks: [
      "You're in 1999. Your phone is the most advanced object on Earth. It can't do anything.",
      "No signal, no internet, no charger. Your supercomputer is now a photo album.",
      "One phone in 1999 could change the world — but not the way you think."
    ],
    beats: [
      "Hour one: no bars, obviously — the networks your phone speaks won't exist for years. You're holding a hundred-billion-dollar R&D program that can play downloaded music and show your photos.",
      "The panic: the charger is the real boss fight. Modern fast-charge bricks don't exist; you're rationing a battery like oxygen — and when it dies, your artifact becomes a paperweight from the future.",
      "The play: it's not the apps — it's the contents. Offline photos, saved articles, and the hardware itself. To the right engineer, that chip is a decade of hints in a metal rectangle.",
      "The trap: show it to anyone credible and your life stops being yours — you're either a fraud, a corporate spy, or the most interesting detainee in the country.",
      "Payoff: the fantasy is knowing the future. The reality is proving it. Knowledge without receipts is just a story — and your only receipt is running out of battery."
    ],
    shotList: [
      "Hook: eyes open, 90s bedroom details, phone lock screen showing today's date glitching.",
      "\"No service\" close-up while dial-up modem sounds bleed from another room.",
      "Battery percentage as a recurring on-screen countdown across every scene.",
      "Engineer's desk: the phone opened up, someone sketching the chip, jaw dropped.",
      "Closer: the dead phone's black mirror reflecting a CRT TV playing static."
    ],
    captions: [
      "1999 + your phone. No signal. No charger. Now what? 📟",
      "The most powerful object on Earth, dying at 4% an hour.",
      "You know the future. Prove it."
    ],
    thumbnails: [
      "4% IN 1999",
      "Paperweight from the future",
      "No signal. No mercy."
    ]
  },
  {
    id: "ar-parallel",
    category: "Alternate Reality",
    title: "What if another you is living your opposite life?",
    image: { glyph: "🪞", from: "#6a5ae0", to: "#2d8a6e" },
    premise: "Take the many-worlds idea seriously for one video: every choice you didn't make, made by someone with your face. Somewhere, the you who said yes. This scenario visits them.",
    tags: ["multiverse", "physics", "choices", "philosophy"],
    safety: "Pop-physics framing — many-worlds is one contested interpretation of quantum mechanics, not settled science. Say so on screen.",
    hooks: [
      "Somewhere, the version of you who said 'yes' is wondering about you too.",
      "Physics has an interpretation where every choice you chickened out of… happened.",
      "This isn't a movie pitch. It's a real (and really contested) reading of quantum mechanics."
    ],
    beats: [
      "The ground rules: many-worlds is a serious, seriously contested interpretation of quantum mechanics — every outcome happens, each in its own branch. Physicists argue about it politely, forever.",
      "The zoom-in: forget cosmic stakes — the branches that haunt people are small. The message you didn't send. The city you didn't move to. The class you dropped.",
      "The visit: picture the ledger — every fork, two of you. The one who stayed; the one who left. Neither knows they're the 'alternate'. From inside, every timeline feels like the main one.",
      "The twist: that's the comfort and the horror in one — there is no main timeline. The other you isn't living your best life; they're living their version, with its own unsent messages.",
      "Payoff: you can't visit the branches. You can only pick which fork today's you creates. The multiverse is a dramatic way of saying: the message is still unsent."
    ],
    shotList: [
      "Hook: mirror shot where the reflection moves half a second late.",
      "Branching-tree animation growing from everyday icons — a phone, moving boxes, keys.",
      "Split-screen day-in-the-life: same face, two routines, one synchronized coffee sip.",
      "Both versions pause at a window at the same moment — opposite skylines.",
      "Closer: a thumb hovering over 'send' on a message. Screen goes dark. Cut."
    ],
    captions: [
      "The you who said yes is also wondering how you're doing 🪞",
      "Many-worlds, but make it personal.",
      "There is no main timeline. That's the comfort AND the horror."
    ],
    thumbnails: [
      "THE OTHER YOU",
      "Every unsent message, sent",
      "No main timeline"
    ]
  },
  {
    id: "ar-typo",
    category: "Alternate Reality",
    title: "What if you found a typo in reality?",
    image: { glyph: "📚", from: "#b8563a", to: "#6a5ae0" },
    premise: "A children's book series everyone remembers one way is spelled another. A movie line millions quote was never said. Play the fun timeline game — then land the real, honestly cooler science.",
    tags: ["mandela effect", "memory", "psychology", "internet culture"],
    safety: "Present the Mandela Effect as a documented memory phenomenon; all timeline talk is clearly playful fiction, not a claim.",
    hooks: [
      "Millions of people remember it with an 'E'. It has never been spelled that way.",
      "One of the most-quoted movie lines ever was never actually said. Check for yourself.",
      "Your brain has a typo. So does everyone else's. The SAME typo. Why?"
    ],
    beats: [
      "The evidence: the bears' name, the monocle that never was, the misquoted 'I am your father' — misrememberings that millions share, identically. That part is documented.",
      "The fun theory: the internet's favorite — timelines merged, and these are the seams. Typos left over from reality's last edit. Great campfire physics. Zero evidence.",
      "The real answer: memory is reconstructive — your brain stores the gist and rebuilds details on demand, using the most plausible spelling and the most quotable phrasing. Same brains, same shortcuts, same 'typo'.",
      "The kicker: knowing this doesn't fix it — you can stare at the real spelling and still feel, bone-deep, that it's wrong. Your certainty is not a truth detector.",
      "Payoff: there's no glitch in the matrix — there's a glitch in the witness. And you're the only witness for everything you've ever seen. Sleep well."
    ],
    shotList: [
      "Hook: book cover with the crucial letter flickering between A and E; viewers vote before the reveal.",
      "Rapid-fire gallery of famous 'effect' examples with ✓/✗ stamps.",
      "Playful VHS-grade 'timeline merge' skit, labeled FICTION on screen.",
      "Brain-as-autocomplete animation: gist goes in, wrong detail comes out.",
      "Closer: narrator holds the actual book to camera. Long pause. \"Feels wrong, doesn't it?\""
    ],
    captions: [
      "Same brain. Same shortcut. Same typo. 📚",
      "The Mandela Effect explained — and why the explanation doesn't help.",
      "Your certainty is not a truth detector."
    ],
    thumbnails: [
      "A or E?",
      "REALITY'S TYPO",
      "You remember it wrong. All of you."
    ]
  },

  /* ---------------- UNSETTLING EVERYDAY ---------------- */
  {
    id: "ue-dejavu",
    category: "Unsettling Everyday",
    title: "What if déjà vu is your brain saving twice?",
    image: { glyph: "💾", from: "#2d8a6e", to: "#5a4a7a" },
    premise: "That shiver of 'I've lived this exact second before' has a leading scientific explanation — and it's basically a filing error. Walk the eerie feeling back to the beautifully mundane machine behind it.",
    tags: ["brain", "memory", "psychology", "everyday"],
    safety: "Grounded in real, still-debated neuroscience hypotheses — present them as leading explanations, not settled fact.",
    hooks: [
      "Déjà vu isn't a glimpse of the future. It might be a save-file error happening live.",
      "That 'I've been here before' feeling? Your brain filed the present under 'past'.",
      "Science's best guess about déjà vu is weirder than the psychic version."
    ],
    beats: [
      "The moment: mid-conversation, the shiver — this exact second has happened before. Everyone knows the feeling; nobody can hold onto it for more than a few seconds.",
      "The leading suspect: a timing hiccup — the experience gets processed through your memory system twice, a beat apart, so the second pass arrives pre-stamped 'familiar'. You're remembering NOW, while it happens.",
      "The supporting suspect: sometimes it's real familiarity in disguise — the room's layout genuinely matches a place you've long forgotten, so the familiarity alarm rings with no visible cause.",
      "The eerie corollary: either way, the feeling of 'having lived this' is fully fake — which means familiarity itself is just a stamp your brain applies. And stamps can misfire. What else is getting stamped wrong?",
      "Payoff: déjà vu isn't evidence you've looped time. It's evidence you never experience the present directly — only your brain's freshly printed copy of it. That should feel fine. Does it?"
    ],
    shotList: [
      "Hook: a mundane kitchen scene plays twice with a subtle echo offset.",
      "Diagram: one 'experience' packet duplicating; the copy gets stamped FAMILIAR.",
      "Overlay: a café floor plan ghost-matching a childhood living room.",
      "Rubber-stamp montage: 'FAMILIAR' slamming onto random moments — one misfire.",
      "Closer: the kitchen scene begins a third time… and cuts to black one beat early."
    ],
    captions: [
      "Déjà vu = your brain saving the same second twice 💾",
      "You never experience the present. Only the printout.",
      "The filing error you've felt your whole life."
    ],
    thumbnails: [
      "SAVED TWICE",
      "Déjà vu, debugged",
      "Your brain's filing error"
    ]
  },
  {
    id: "ue-mirror",
    category: "Unsettling Everyday",
    title: "What if mirrors have a delay you've never caught?",
    image: { glyph: "🪟", from: "#3b4368", to: "#2dbf8b" },
    premise: "A pure thought experiment: your reflection lags by a fraction of a second — always has — and your brain smooths it over, the way it smooths over your blind spot and your blinks. You could never prove it wrong from the inside.",
    tags: ["perception", "philosophy", "everyday", "eerie"],
    safety: "Explicit fiction — mirrors are physics-perfect. The real payload is true perception science (saccadic masking), clearly separated.",
    hooks: [
      "You have never once seen your own eyes move in a mirror. Try it right now.",
      "Your brain edits out roughly half an hour of your vision every day. What else is it smoothing over?",
      "The mirror-delay theory is fake. The reason you can't disprove it isn't."
    ],
    beats: [
      "The claim: every mirror lags — a few dozen milliseconds, always. Nobody's ever caught it, because the thing checking the mirror is the same brain that smooths the gap.",
      "The real hook: that part is fiction, but this isn't — every time your eyes dart, your brain blanks the blur and backfills the moment. Added up: on the order of half an hour a day, edited out. You never noticed.",
      "The demonstration: look at one of your eyes in a mirror, then the other. You will never see your own eyes mid-move. Anyone watching you can. You physically cannot.",
      "The unravel: blinks, blind spots, saccades — your seamless 'live feed' of reality is a heavily produced broadcast with invisible cuts. The delay theory is fake; the editing room is real.",
      "Payoff: you can't catch the mirror lagging because you've never seen an unedited frame of anything. The reflection is fine. The cameraman is the mystery."
    ],
    shotList: [
      "Hook: locked-off mirror shot; the reflection blinks — did it? The replay refuses to confirm.",
      "On-screen challenge: 'watch your own eyes move in a mirror' — hold a beat of silence so viewers actually try.",
      "Editing metaphor: real life on a video-editor timeline, cuts appearing invisibly.",
      "Counter graphic: '~30–40 min/day' accumulating over ordinary b-roll.",
      "Closer: the camera pushes slowly past the narrator INTO the mirror; cut before contact."
    ],
    captions: [
      "Try it right now: watch your own eyes move in a mirror. You can't. 🪟",
      "The delay is fiction. The editing is real.",
      "Your vision has a director's cut. You've never seen the raw footage."
    ],
    thumbnails: [
      "MIRRORS LAG?",
      "You can't see this",
      "The invisible cut"
    ]
  },
  {
    id: "ue-wrongnumber",
    category: "Unsettling Everyday",
    title: "What if every wrong-number text was meant for you?",
    image: { glyph: "📩", from: "#b8563a", to: "#151a30" },
    premise: "'Sorry, wrong number' — every so often, a stranger's life briefly opens a door into yours. Run the eerie premise, then land on the true, stranger fact: some of those texts aren't mistakes at all.",
    tags: ["phones", "strangers", "scams", "everyday"],
    safety: "Includes real scam-awareness info (wrong-number 'pig butchering' scams). Keep it protective, not fear-mongering; the fictional frame is clearly labeled.",
    hooks: [
      "That 'wrong number' text was step one of a script. Here's the rest of it.",
      "What if wrong numbers aren't wrong? Fun theory — until you learn about the real ones.",
      "Every so often a stranger texts you 'by accident'. Sometimes it isn't one."
    ],
    beats: [
      "The premise, fictional version first: no text is random — each 'wrong number' is a fork, a tiny audition for a different life. Reply, and a door opens. Spooky, fun, fake.",
      "The turn: now the real version — entire scam operations open with a harmless wrong-number text. 'Hi, is this Anna from the gallery?' The mistake is the bait; your politeness is the hook.",
      "The mechanics: they don't want money on day one — they want conversation. Weeks of friendly small talk, then an investment tip. The long con has an industry name, and it's ugly: pig butchering.",
      "The defense: it costs nothing to not reply. Real wrong numbers don't follow up, don't compliment you, and don't pivot to crypto. Delete, report, move on.",
      "Payoff: the fictional version asked 'what if every wrong number was meant for you?' The real answer: some are — and that's exactly why you shouldn't answer. The mystery door is a sales funnel."
    ],
    shotList: [
      "Hook: lock-screen close-up, an innocent 'wrong number' text sliding in; room tone drops.",
      "Fictional montage: branching doors opening off a hallway of chat bubbles, dreamlike.",
      "Hard cut to reality: the scam flowchart, step by step, clinical lighting.",
      "Side-by-side: 'real wrong number' vs 'bait' texts with the tells highlighted.",
      "Closer: a thumb hovers over reply… then swipes delete. Screen locks. Silence."
    ],
    captions: [
      "The wrong-number text that wasn't 📩 (real scam, real script)",
      "Fun spooky theory → actual PSA. Sorry, it's both.",
      "Real wrong numbers don't follow up. Remember that."
    ],
    thumbnails: [
      "IT WASN'T A MISTAKE",
      "The politeness trap",
      "Don't answer 'Anna'"
    ]
  },

  /* ---------------- SCARY/WEIRD ---------------- */
  {
    id: "sw-paralysis",
    category: "Scary/Weird",
    title: "What if everyone's sleep paralysis demon is the same?",
    image: { glyph: "👁️", from: "#151a30", to: "#b83a6e" },
    premise: "Different centuries, different continents, no contact between them — and the reports rhyme: pressure on the chest, a figure in the doorway. Ask the campfire question, then give the neuroscience its full, genuinely fascinating due.",
    tags: ["sleep", "brain", "folklore", "horror"],
    safety: "Real phenomenon affecting real people — explain the science, avoid ridicule, and end on the 'common and harmless' reassurance.",
    hooks: [
      "A hag in 1690s Newfoundland. A shadow man on a forum last night. Same visitor. No contact between them.",
      "Sleep paralysis reports across 400 years keep describing the same figure. Here's why.",
      "Your brain ships with a monster generator. Tonight it might run. Here's the manual."
    ],
    beats: [
      "The pattern: Newfoundland called it the Old Hag. Japan calls it kanashibari. Medieval Europe painted incubi. Modern forums post about the Shadow Man. Different worlds — same scene: awake, frozen, watched.",
      "The campfire take: one entity, patient, wearing whatever face each era expects. Great horror premise. Now here's the part that's actually true — and somehow weirder.",
      "The science: sleep paralysis is REM sleep's muscle-lock outlasting the dream — you wake up, the body is still locked, and the dreaming machinery keeps painting onto the real room. A hallucination using your actual bedroom as the canvas.",
      "The convergence: why the same figure everywhere? Because the fear circuitry doing the painting is standard human equipment — threat detection expects an intruder, so it renders one: humanoid, dark, in the doorway. Same hardware, same monster.",
      "Payoff: the demon is real in the only way that matters to your 3am brain — and completely harmless in every way that matters to the rest of you. It passes in seconds. The visitor was you all along."
    ],
    shotList: [
      "Hook: era-hopping match cut — woodcut, oil painting, grainy webcam — same silhouette in each doorway.",
      "Map graphic: names for the phenomenon appearing across continents and centuries.",
      "Calm diagram: the REM switch stuck 'on', a dream projector spilling into a real bedroom.",
      "The 'render' shot: doorway darkness resolving into a figure, then dissolving into visual noise.",
      "Closer: morning light in the same doorway, empty; one reassuring line on screen."
    ],
    captions: [
      "400 years. Five continents. Same visitor. 👁️ (the science is wilder than the myth)",
      "Your brain ships with a monster generator. Here's the documentation.",
      "Kanashibari, the Old Hag, the Shadow Man — one explanation."
    ],
    thumbnails: [
      "SAME DEMON. EVERYWHERE.",
      "The 3AM visitor, explained",
      "Your brain's monster engine"
    ]
  },
  {
    id: "sw-bloop",
    category: "Scary/Weird",
    title: "What if the ocean made a sound we couldn't explain?",
    image: { glyph: "🌊", from: "#1a4a6e", to: "#151a30" },
    premise: "In 1997, underwater microphones thousands of kilometers apart caught one of the loudest sounds ever recorded in the ocean. The official explanation took years — and the internet never fully let go. A scenario about the ocean's talent for keeping secrets.",
    tags: ["ocean", "sound", "mystery", "science"],
    safety: "Real event (the Bloop) — state the accepted icequake explanation clearly; anything beyond it is labeled speculation.",
    hooks: [
      "In 1997 the ocean said something. It was loud enough to be heard across an entire sea.",
      "The loudest unexplained underwater sound ever recorded got an official answer. The internet said 'hmm.'",
      "We've mapped the Moon better than our own ocean floor. Then the ocean cleared its throat."
    ],
    beats: [
      "The event: summer 1997 — hydrophones roughly 3,000 kilometers apart pick up the same ultra-low rumble. Researchers nickname it the Bloop. For years, no confirmed source. All documented.",
      "The monster years: the sound's profile resembled a biological call — but scaled to that volume, the 'animal' would dwarf a blue whale. The internet did what the internet does.",
      "The answer: the accepted explanation eventually landed — an icequake, a massive frozen shelf cracking near Antarctica. Ice, not leviathan. Scientists consider it settled.",
      "The honest residue: here's why the story never dies — the large majority of the deep ocean floor remains unmapped in detail. The Bloop was ice. The next unexplained sound gets to audition all over again.",
      "Payoff: the scary thing was never a monster — it's that Earth still has a basement with the lights mostly off. The ocean doesn't keep secrets on purpose. It just doesn't know we're asking."
    ],
    shotList: [
      "Hook: sonar-style waveform crawling across the screen, pitch-shifted rumble underneath.",
      "Map: two hydrophone points 3,000 km apart, detection rings overlapping.",
      "Scale graphic: blue whale silhouette, then the hypothetical 'caller' dwarfing it — stamped MYTH.",
      "Ice-shelf calving footage, the waveform syncing to the cracks — stamped CONFIRMED.",
      "Closer: slow descent into dark water, a flashlight beam swallowed; 'mostly unmapped' fades in."
    ],
    captions: [
      "1997: the ocean said one thing. We spent years asking 'what?' 🌊",
      "It was ice. Probably. Definitely. It was ice.",
      "Earth has a basement. The lights are mostly off."
    ],
    thumbnails: [
      "THE SOUND (1997)",
      "Bigger than a whale?",
      "Ice. Probably."
    ]
  },
  {
    id: "sw-onlyone",
    category: "Scary/Weird",
    title: "What if you're the only one fully awake right now?",
    image: { glyph: "🎭", from: "#5a4a7a", to: "#b8a13a" },
    premise: "A philosophy-class classic given the short-form treatment: you can verify your own inner life, and literally no one else's. Walk to the edge of solipsism, look over, and come back with the good news.",
    tags: ["philosophy", "consciousness", "mind", "thought experiment"],
    safety: "Philosophical thought experiment — steer well clear of 'other people don't matter' framing; land firmly on empathy and the argument FOR other minds.",
    hooks: [
      "You have never once verified that anyone else is conscious. Not once. You can't.",
      "Philosophy's creepiest question has a name — and thinking about it too long is a rite of passage.",
      "Everyone around you might be running on autopilot. Here's why philosophers say: relax."
    ],
    beats: [
      "The setup: you know YOU'RE experiencing this moment — the one fact you get for free. Everyone else? Inferred from the outside: faces, words, behavior. You've never checked directly. You can't.",
      "The vertigo: philosophers call it the problem of other minds — taken seriously, the crowd around you could in principle be all surface, no inner light. Centuries of debate; no knockout proof.",
      "The turn: but notice what the doubt costs — the same reasoning that doubts other minds should doubt your memories, your senses, yesterday. Radical doubt doesn't stop where it's convenient. It eats everything.",
      "The rescue: the boring, beautiful answer — other people are built like you and behave like you. They wince, laugh, hesitate like you. Same hardware, same behavior: the best explanation is that the lights are on everywhere.",
      "Payoff: you can't PROVE the person next to you is awake inside — but you couldn't function one honest day believing otherwise. Empathy isn't naive. It's the smartest bet available. Take it."
    ],
    shotList: [
      "Hook: crowded crosswalk timelapse; everyone blurs except one sharp figure.",
      "Graphic: one lit window in a dark apartment block, question marks over the rest.",
      "Domino sequence: 'doubt others' toppling into 'doubt memory', 'doubt senses', 'doubt yesterday'.",
      "Warm reversal: the apartment block again — windows lighting up one by one.",
      "Closer: two strangers laugh at the same street moment; freeze; 'same hardware. take the bet.'"
    ],
    captions: [
      "The one fact you get for free — and the billions you take on faith 🎭",
      "Solipsism: the thought experiment with a built-in exit.",
      "Empathy is the smartest bet available. Philosophy said so."
    ],
    thumbnails: [
      "ONLY YOU?",
      "The unverifiable crowd",
      "Lights on everywhere"
    ]
  },

  /* ---------------- SCARY STORY ----------------
     Narrative category: true-feeling short horror told straight, no "what if"
     framing. Picture-only by design — the pipeline defaults these to the
     dark visual style and swaps in scary-story CTA + hashtags. */
  {
    id: "ss-lastdive",
    category: "Scary Story",
    title: "The dive was planned for 40 minutes",
    image: { glyph: "🤿", from: "#0a1420", to: "#8a2431" },
    premise: "A cave diver follows his own guideline into a flooded cave system he's mapped a dozen times. The line is right where he left it. The problem is what's clipped to it — a marker he didn't place, pointing the wrong way.",
    tags: ["cave diving", "survival", "underwater", "scary story"],
    safety: "Fictional story inspired by real cave-diving accident reports. No real victims or incidents depicted; dive-safety details kept realistic, not instructional.",
    hooks: [
      "Cave divers have a rule: the line is life. He found a second line — and it wasn't his.",
      "40 minutes of air. 35 minutes of cave. The math worked until the silt came down.",
      "The last thing his dive log says is 'passage wider than mapped.' It isn't."
    ],
    beats: [
      "He drops below the surface at 9:04 AM, alone, the way he's done a dozen times. His guideline runs into the dark like a thread through a needle. Plan: 40 minutes, 300 feet back, touch the old gate grate, turn around.",
      "At the squeeze — the point where his tanks scrape both walls — he notices it. A line marker clipped to his guideline, the plastic arrow kind divers use to point the way OUT. Except this arrow points deeper in. He didn't clip it there. Nobody dives this cave.",
      "He tells himself it's old, left from a survey years ago. Then his fin catches the floor and the silt comes up like smoke filling a room. Visibility goes from sixty feet to zero in eight seconds. Now the line in his hand is the only thing that's real.",
      "He follows it by touch, breathing slow, counting knots — and his glove finds a second marker. Then a third. All pointing deeper. And under his fingers, the line changes: his braided nylon becomes something older, stiffer. He is no longer holding his own line.",
      "He backtracks hand over hand and surfaces at 9:51 with 200 psi to spare. That afternoon he pulls his gear up and finds every arrow on the recovered line pointing the right way — toward the exit. Whatever line he was holding down there, it wasn't the one he pulled out."
    ],
    shotList: [
      "Hook: a lone diver's silhouette descending into a flooded cave mouth, flashlight beam swallowed by black water.",
      "Close-up: a gloved hand following a thin guideline through a narrow rock squeeze, tanks scraping stone.",
      "Macro shot: a plastic line arrow clipped to the guideline, pointing into darkness, caught in the flashlight beam.",
      "Zero visibility: a wall of brown silt blooming through the beam, a hand gripping the line the only visible thing.",
      "Surface shot: the diver's head breaking calm water in a dark cave pool, gasping, dawn light from the entrance.",
      "Closer: coiled recovered dive line on wet stone, all arrows pointing one way, one frame held too long."
    ],
    captions: [
      "The line is life. So whose line was he holding? 🤿",
      "40 minutes of air. And arrows pointing the wrong way.",
      "Cave divers trust the line more than their own eyes. That's the problem."
    ],
    thumbnails: [
      "THE SECOND LINE",
      "Arrows pointed IN",
      "40 minutes of air"
    ]
  },
  {
    id: "ss-nightshift",
    category: "Scary Story",
    title: "The night shift keeps a list",
    image: { glyph: "🏥", from: "#0d1018", to: "#5a4a7a" },
    premise: "Every hospital has unofficial rules the day shift never hears about. At St. Alder's, the night nurses keep theirs taped inside a supply-closet door — seven rules, handwritten, added to one at a time over forty years. A new nurse just found out why rule four exists.",
    tags: ["hospital", "night shift", "rules", "scary story"],
    safety: "Fictional 'rules' horror story set in an invented hospital. No real institutions, patients, or medical events depicted.",
    hooks: [
      "Hospital night shifts have rules the day shift never learns. Rule four is why nurses quit.",
      "The list is handwritten. Seven rules. Forty years of handwriting. One pen never came back.",
      "Her trainer said: 'If the fourth-floor call bell rings twice, you send the FLOAT nurse.' She asked why. Nobody laughed."
    ],
    beats: [
      "Her first night shift, the charge nurse walks her to a supply closet and points at a paper taped inside the door. Seven handwritten rules, different pens, different decades. 'Read it. Don't photograph it. It stays in the closet.'",
      "Most are almost normal. Rule two: count the wheelchairs by the east elevator — there are four; if there are five, take the stairs. Rule six: the vending machine on three is allowed to eat your dollar. Let it.",
      "Rule four is the one underlined twice: if room 4B's call bell rings twice in a row, you do not answer it yourself — you send whoever is floating that night. 4B has been a storage room since 1987. The bell was disconnected in 1987. It rings maybe twice a year.",
      "At 3:12 AM in her fourth week, the board lights up: 4B. Then again. She's alone at the station — no float tonight. The rules don't cover that. So she does the thing the list was written to prevent: she goes to see, and the door to 4B is already open.",
      "Inside: shelving, dust, and a call-bell cable hanging loose exactly as it has for forty years — nowhere near a button. She reports it. The charge nurse doesn't ask what she saw. She just hands her a pen and says, 'You get to write rule eight.'"
    ],
    shotList: [
      "Hook: a long empty hospital corridor at night, half the fluorescent lights off, one flickering at the far end.",
      "Close-up: a yellowed handwritten list taped inside a metal supply-closet door, seven rules in different inks.",
      "Detail shot: a row of four wheelchairs by an elevator in low light, a fifth shape in shadow at the end.",
      "The nurses' station at 3 AM: a call-board lighting up '4B', a young nurse's face lit from below by the panel.",
      "POV walking slowly toward a door standing ajar at the end of a dark storage corridor, flashlight beam trembling.",
      "Closer: an old pen held out over the list, one blank space under rule seven, hand hesitating."
    ],
    captions: [
      "Night-shift rules aren't in the handbook. They're in the closet. 🏥",
      "Rule 4: never answer 4B yourself. There's no rule for being alone.",
      "Forty years of handwriting. She gets to write rule eight."
    ],
    thumbnails: [
      "RULE FOUR",
      "The bell rang twice",
      "Night shift rules"
    ]
  },
  {
    id: "ss-stairs",
    category: "Scary Story",
    title: "The staircase in the woods",
    image: { glyph: "🌲", from: "#0c1410", to: "#3b4368" },
    premise: "Search-and-rescue volunteers walk grid patterns through wilderness nobody visits. They all report the same thing eventually: a staircase, freestanding, immaculate, miles from any road. The briefing covers it in one line: mark the coordinates, keep walking.",
    tags: ["forest", "search and rescue", "hiking", "scary story"],
    safety: "Fictional story in the campfire/internet-legend tradition (freestanding stairs in the woods). No real SAR teams, cases, or missing persons referenced.",
    hooks: [
      "Search-and-rescue teams have a one-line briefing about stairs in the woods: mark it, don't climb it.",
      "Twelve miles from the nearest road, he found a staircase. Carpeted. Clean. Standing alone.",
      "The weird part isn't the stairs. It's that his GPS logged him standing there for 51 minutes. He remembers 5."
    ],
    beats: [
      "His first season on volunteer search-and-rescue, the briefing is mostly boring: grid spacing, whistle signals, hydration. Then the old-timer running it says, without looking up: 'If you find stairs, log the location and keep moving.' Nobody asks. He assumes it's a joke.",
      "Two summers later he's sweeping a ravine twelve miles from the nearest trailhead when the trees open up. A staircase. Freestanding, like a house was lifted off it. Oak banister, carpet runner, no weathering, no leaves on the steps — in a forest that buries everything by October.",
      "He circles it twice. No foundation, no rot, no bird has touched it. His radio crackles static on a channel that was clear all morning. And the forest around it is quiet in a way forests aren't — no insects, like the volume was turned down in a circle.",
      "He does what the briefing said: logs the coordinates, takes one photo, keeps walking. At debrief, his GPS track shows him stationary at that clearing for 51 minutes. He remembers five. The photo on his phone shows the clearing, the trees, the carpet-flattened grass — and no stairs.",
      "The old-timer takes his report without blinking and files it in a folder that is not thin. 'You did it right,' he says. He never says what happens when someone does it wrong. But the grid maps have small red Xs on them, and nobody searches those squares."
    ],
    shotList: [
      "Hook: dense old-growth forest in flat grey light, a clean wooden staircase standing alone in a clearing.",
      "A search-and-rescue volunteer in an orange vest checking a handheld GPS among huge trees, breath visible.",
      "Low angle up the staircase: polished banister, carpet runner, treetops where a second floor should be.",
      "Close-up: a radio in a gloved hand, static bars dancing, the volunteer's eyes fixed on something off-frame.",
      "Overhead map graphic: a search grid with a handful of squares marked with small red Xs.",
      "Closer: an old filing folder labeled 'STRUCTURES' dropped onto a desk, thick with decades of reports."
    ],
    captions: [
      "SAR briefing, one line: if you find stairs, keep walking. 🌲",
      "51 minutes on the GPS. He remembers 5.",
      "The photo shows the clearing. It doesn't show the stairs."
    ],
    thumbnails: [
      "STAIRS. ALONE.",
      "Mark it. Don't climb it.",
      "51 missing minutes"
    ]
  },
  {
    id: "ss-lookout",
    category: "Scary Story",
    title: "The fire lookout's last radio check",
    image: { glyph: "📻", from: "#141008", to: "#b8563a" },
    premise: "Fire lookouts spend whole seasons alone in glass towers, checking in by radio twice a day. Dispatch logs every word. Her tower's log for August 14th shows a check-in at 9 PM — routine, calm, her voice. She was asleep by 8.",
    tags: ["wilderness", "radio", "isolation", "scary story"],
    safety: "Fictional story set in an invented fire-lookout post. No real agencies, towers, or personnel depicted.",
    hooks: [
      "Fire lookouts radio in twice a day. Dispatch has her 9 PM check-in on tape. She was asleep by 8.",
      "Alone in a glass tower, 40 miles from anyone — and dispatch keeps answering someone who isn't her.",
      "The recording is her voice. Her call sign. Her cadence. One detail is wrong: it describes tomorrow's weather."
    ],
    beats: [
      "Third season in the tower: 14 feet of glass on a mountain's shoulder, a radio, a logbook, and a horizon she knows by heart. Check-in at 9 AM, check-in at 9 PM, same script every day: call sign, visibility, weather, 'all quiet.'",
      "In August the storms come and she starts sleeping early. One morning dispatch thanks her for 'last night's report.' She didn't make one. She laughs it off as a logging error — until the supervisor reads it back, and it's her voice on the recording. Her call sign. Her rhythm.",
      "The reports keep coming, always nights she's asleep, always flawless — except each one describes the NEXT day's weather. Wind shift at noon: correct. Dry lightning on the north ridge: correct, to the hour. Dispatch is getting tomorrow's mountain, one night early.",
      "She stops sleeping and sits by the radio with the volume up. At 9:02 PM the handset clicks like a throat clearing, and she hears her own voice go out on the channel — calm, easy, mid-report — while her thumb is nowhere near the transmit key. It reads the weather. Then it says something new: 'Smoke visible. Southeast. All quiet.'",
      "Southeast is the one direction her tower can't see — the ridge blocks it. She logs it anyway. Two days later a crew finds a lightning strike smoldering exactly there, caught so early it never made the news. The voice never transmits again. Her last logbook entry that season isn't a weather line. It's a thank-you."
    ],
    shotList: [
      "Hook: a tiny glass fire-lookout tower on a mountain ridge at dusk, one warm light against a wall of storm clouds.",
      "Interior: a woman by lantern light at an old radio set, logbook open, endless dark forest beyond the glass.",
      "Extreme close-up: a radio handset on its hook, the transmit light glowing red, no hand anywhere near it.",
      "Her face lit by the radio dial at night, eyes wide, listening to her own voice come out of the speaker.",
      "Dawn wide shot: a thin column of smoke rising from a ridge line, small and early against a pink sky.",
      "Closer: a weathered logbook page, weather entries in neat handwriting, the last line reading only 'thank you.'"
    ],
    captions: [
      "Dispatch has her 9 PM check-in on tape. She was asleep. 📻",
      "The voice knew tomorrow's weather. Then it saw smoke.",
      "Alone in a glass tower — but the radio kept her company."
    ],
    thumbnails: [
      "HER OWN VOICE",
      "The 9 PM check-in",
      "It saw the smoke first"
    ]
  },
  {
    id: "ss-doorbell",
    category: "Scary Story",
    title: "The doorbell only records him at 3:33",
    image: { glyph: "🚪", from: "#0d0d12", to: "#6a5ae0" },
    premise: "A smart doorbell that triggers on motion, every night, at exactly 3:33 AM. Same figure at the end of the driveway. Every night one step closer. The manufacturer's support team stops replying after she sends the eleventh clip.",
    tags: ["smart home", "camera", "night", "scary story"],
    safety: "Fictional suburban horror story. No real products, companies, or events depicted; avoids home-invasion realism in favor of the uncanny.",
    hooks: [
      "Her doorbell records a stranger every night at 3:33. Every night, one step closer.",
      "Motion alerts don't lie. Except hers fire at the same second every night — for something the camera can barely see.",
      "Clip 1: end of the driveway. Clip 11: close enough to count buttons. Clip 12 is why she moved."
    ],
    beats: [
      "The alert wakes her the first time: MOTION DETECTED, 3:33 AM. The clip shows her empty driveway in grainy night vision — and at the very edge, by the mailbox, a figure standing still. Not walking past. Facing the house. She checks the yard in the morning: nothing.",
      "It happens again the next night. 3:33 AM exactly — not 3:32, not 3:34. Same figure, same stillness. But tonight he's standing three feet past the mailbox. She scrubs both clips frame by frame. He never moves in either one. He's just... further along.",
      "Night after night the clips stack up, each one a single step closer, like frames of a film played one per day. Support says it's 'likely a looping firmware artifact.' Then she sends clip eleven — close enough to see coat buttons and that the face is slightly, politely wrong — and support stops replying.",
      "She stops sleeping through the alert and sits by the window at 3:30 with the lights off. At 3:33 her phone buzzes in her hand: MOTION DETECTED. The driveway below her is empty. It has been empty the whole time. Whatever the camera sees, it doesn't need her eyes to agree.",
      "Clip twelve is the last one on the account. It isn't the driveway. The lens is looking down the upstairs hallway — a camera she doesn't own, an angle that doesn't exist — at her bedroom door, standing open. She doesn't watch it twice. Some houses you don't sell; you just leave."
    ],
    shotList: [
      "Hook: grainy black-and-white doorbell night footage of a suburban driveway, a still figure at the far edge by a mailbox, timestamp 3:33 AM.",
      "A woman's face lit only by her phone in a dark bedroom, the motion alert glowing on the screen.",
      "Split grid of doorbell clips side by side, the same figure incrementally closer in each frame, timestamps identical.",
      "Extreme close-up of a laptop screen scrubbing footage: a coat button, a face just out of focus, cursor trembling on the pause bar.",
      "Wide shot: her silhouette at the dark window at 3:33, phone buzzing in hand, the driveway below completely empty.",
      "Closer: a FOR SALE sign at the end of a driveway at dawn, the doorbell camera above it with its lens taped over."
    ],
    captions: [
      "Every night. 3:33. One step closer. 🚪",
      "Support stopped replying after clip eleven.",
      "The last clip wasn't from the driveway."
    ],
    thumbnails: [
      "3:33 AM",
      "One step closer",
      "Clip 12"
    ]
  },

  /* ---------------- TRUE HISTORY ----------------
     Narrative category #2: real, documented events told documentary-style.
     Picture-only by design — the pipeline defaults these to the archival
     visual style and swaps in true-history CTA + hashtags. Facts must stay
     accurate; anything debated is flagged in the narration itself. */
  {
    id: "th-dancingplague",
    category: "True History",
    title: "The town that couldn't stop dancing",
    image: { glyph: "🩰", from: "#3d2f1a", to: "#8a2431" },
    premise: "Strasbourg, July 1518. A woman named Frau Troffea steps into the street and starts dancing. She doesn't stop for days — and within a month, hundreds of townspeople are dancing with her, many literally unable to quit. This is one of history's best-documented mass mysteries.",
    tags: ["medieval", "mystery", "medicine", "true history"],
    safety: "Real, documented event (Strasbourg dancing plague, 1518). Casualty details from contemporary accounts are debated and framed as such; modern explanation (mass psychogenic illness) presented as the leading theory, not settled fact.",
    hooks: [
      "In 1518, a whole town started dancing — and physically couldn't stop.",
      "The city's cure for a dancing plague? Hire a band. It went exactly as badly as you think.",
      "One woman started dancing in the street. A month later it was 400 people. This is real."
    ],
    beats: [
      "Strasbourg, July 1518. A woman called Frau Troffea walks out of her house and begins to dance. No music, no festival, no smile. She dances until she collapses from exhaustion, sleeps, gets up — and keeps dancing. After nearly a week, dozens have joined her.",
      "The city's doctors rule out the stars and blame 'hot blood.' Their prescription: the dancers should dance it out of their systems. The council hires musicians, opens guild halls, even builds a stage. Official policy is now MORE dancing.",
      "It backfires completely. The music draws in new dancers, and by August, chronicles put the number around 400. Contemporary accounts describe bloody feet, people begging for help mid-dance, and some dancers reportedly dying of strokes and exhaustion — though historians still argue over the death toll.",
      "The city reverses course: dancing is banned, and in September the remaining dancers are loaded into wagons and taken to a mountain shrine of Saint Vitus to be blessed. Within weeks, the plague fades — as strangely as it began.",
      "The best modern explanation: mass psychogenic illness — a stress epidemic in a town crushed by famine and disease, where people BELIEVED a dancing curse was possible. The eerie part? It had happened before. At least seven dancing plagues hit the region in the centuries before Strasbourg."
    ],
    shotList: [
      "Hook: a lone woman in rough 16th-century clothes dancing in an empty cobblestone street, medieval townsfolk staring from doorways.",
      "Candle-lit interior: physicians in dark robes arguing over an open medical folio, a dancing figure visible through the window behind them.",
      "Wide shot of a crowded medieval square: dozens of exhausted dancers, hired musicians playing on a wooden stage, oil-painting texture.",
      "Close-up: worn leather shoes and bruised feet still moving on cobblestones, dawn light, long shadows.",
      "A creaking wagon of slumped dancers winding up a mountain road toward a small stone chapel.",
      "Closer: an old chronicle page in Latin script beside a single burning candle, quill resting on the desk."
    ],
    captions: [
      "Strasbourg, 1518: the plague you could hear coming — it had a beat. 🩰",
      "The official cure was a hired band. It made everything worse.",
      "400 people. Weeks of dancing. Fully documented. Still unsettling."
    ],
    thumbnails: [
      "THE DANCING PLAGUE",
      "1518: no one could stop",
      "The cure was a band"
    ]
  },
  {
    id: "th-emuwar",
    category: "True History",
    title: "The war Australia lost to birds",
    image: { glyph: "🪶", from: "#8a6d2f", to: "#3a6ea5" },
    premise: "In 1932, Australia sent soldiers with machine guns to fight 20,000 emus destroying wheat farms. The military filed reports, a major commanded the operation, Parliament debated it — and the emus won. Every part of this story is real.",
    tags: ["australia", "military", "animals", "true history"],
    safety: "Real, documented event (the 'Emu War', Western Australia, 1932). Told for its absurdity, at the expense of the humans, not the animals; casualty figures are the officially reported ones.",
    hooks: [
      "In 1932, Australia declared war on birds. The birds won. This is a real military operation.",
      "Two machine guns, 10,000 rounds, one major — versus 20,000 emus. Guess who won.",
      "An actual army major wrote in an actual report that emus could 'face any army in the world.'"
    ],
    beats: [
      "Western Australia, 1932. Twenty thousand emus come marching out of the outback into the wheat fields of Campion — right as struggling farmers, many of them WWI veterans, are trying to bring in a harvest. The farmers ask the government for help. The government sends the army.",
      "Enter Major Meredith of the Royal Australian Artillery, two Lewis machine guns, and 10,000 rounds of ammunition. The plan: mow down the flocks. First contact, the emus do something no one briefed him on — they scatter into small groups and sprint in every direction at 50 kilometers an hour.",
      "It gets worse. The gun jams during one ambush. A truck-mounted gun can't shoot straight on the rough ground, and the emus outrun the truck anyway. Observers swear each mob seems to have a lookout bird posted while the others feed. The army is being out-generaled by poultry.",
      "After about a month, the score: roughly 10,000 rounds fired, fewer than a thousand confirmed emus down, most of the 20,000 still eating wheat. Meredith reports, apparently sincerely, that a unit with the emu's bullet-taking ability could 'face any army in the world.' When Parliament asks if medals will be awarded, the answer given: the medals should go to the emus.",
      "The military withdraws, defeated by birds — and the actual fix turns out boring: bounties and better fences, which work. The Emu War survives every fact-check thrown at it, and the emu still stands proudly on Australia's coat of arms. It earned it."
    ],
    shotList: [
      "Hook: a line of emus striding through a golden wheat field at dawn, heads high, shot like a war film's opening.",
      "Sepia archival look: 1930s Australian soldiers in slouch hats setting up a Lewis machine gun on a dusty farm track.",
      "Action shot: emus sprinting in all directions through scrubland, dust flying, comically fast, low camera angle.",
      "A vintage truck bouncing over rough paddocks, gunner clinging on, emus effortlessly pulling away ahead.",
      "Officer at a field desk writing a report by lamplight, map of Western Australia pinned behind him.",
      "Closer: Australia's coat of arms, slow push-in on the emu, golden light."
    ],
    captions: [
      "1932: Australia vs 20,000 emus. Official military operation. 🪶",
      "10,000 rounds. The emus held the field.",
      "The medals, said Parliament, should go to the emus."
    ],
    thumbnails: [
      "THE EMU WAR",
      "Australia lost. To birds.",
      "10,000 rounds, 0 victory"
    ]
  },
  {
    id: "th-carrington",
    category: "True History",
    title: "The night the sky caught fire",
    image: { glyph: "🌌", from: "#151a30", to: "#b8563a" },
    premise: "September 1859: auroras blaze over Cuba, gold miners get up for breakfast at 1 AM thinking it's dawn, and telegraph offices catch fire as the wires themselves surge with current. The Carrington Event is the biggest solar storm on record — and the reason power-grid planners still lose sleep.",
    tags: ["space", "sun", "victorian", "true history"],
    safety: "Real, documented event (the Carrington Event, 1859) with real named observers. Modern-impact figures are estimates from published studies, framed as estimates.",
    hooks: [
      "In 1859 the northern lights reached Cuba — and telegraph wires started sparking on their own.",
      "A British astronomer watched the sun flash white. Seventeen hours later, Earth's sky caught fire.",
      "Telegraph operators unplugged their batteries — and the messages kept sending. On aurora power."
    ],
    beats: [
      "September 1st, 1859. Richard Carrington, a British astronomer sketching sunspots through his telescope, watches two beads of blinding white light flare on the sun's surface — the first solar flare ever observed. He has no idea a billion-ton cloud of charged particles is now racing toward Earth.",
      "About seventeen hours later, it hits. Auroras erupt so far south they're seen over Cuba and Colombia. In the Rocky Mountains, the glow is so bright that gold miners get up and start cooking breakfast, convinced it's morning. People read newspapers by the light of the sky at midnight.",
      "Then the wires go strange. The world's brand-new telegraph network — Victorian internet — starts surging: operators get shocked at their keys, pylons throw sparks, and telegraph paper catches fire in offices on two continents.",
      "Strangest of all: some operators disconnect their batteries — and keep transmitting anyway. The Boston operator asks Portland how they're sending with no power. The aurora's current in the wires is running the line by itself. That exchange is preserved in the historical record.",
      "In 1859, the damage was singed telegraph offices. Run the same storm today and studies put the bill in the trillions — transformers, satellites, GPS, power grids, months of blackout. And in July 2012, a Carrington-class blast crossed Earth's orbit... through the spot we'd occupied nine days earlier. The sun isn't done."
    ],
    shotList: [
      "Hook: violent red and green auroras blazing over a Victorian city skyline, gaslights below, people staring upward in the street.",
      "A bearded Victorian astronomer at a brass telescope, one eye to the eyepiece, sunlight projecting a sunspot sketch onto paper.",
      "Miners' camp in the Rockies at night: men in suspenders cooking over a fire under a sky glowing like sunrise.",
      "Interior telegraph office: an operator jerking his hand back from a sparking brass key, paper tape smoking on the desk.",
      "Close-up: a disconnected battery on a wooden desk, the telegraph key beside it clicking by itself under aurora light through the window.",
      "Modern contrast shot: a city power grid at dusk seen from above, then a slow fade of entire districts going dark."
    ],
    captions: [
      "1859: auroras in Cuba, sparks in the wires, fire in the sky. 🌌",
      "They unplugged the batteries. The telegraph kept sending.",
      "The biggest solar storm on record — and 2012 was a near miss."
    ],
    thumbnails: [
      "THE SKY CAUGHT FIRE",
      "1859's solar storm",
      "It almost hit in 2012"
    ]
  },
  {
    id: "th-marathon1904",
    category: "True History",
    title: "The most cursed race ever run",
    image: { glyph: "🏃", from: "#8a6d2f", to: "#b8563a" },
    premise: "The 1904 Olympic marathon in St. Louis: 90-degree heat, one working water stop, a winner carried across the line on rat poison and brandy, a 'champion' who did 11 miles by car, and a Cuban postman who paused mid-race for a nap. Every detail is documented.",
    tags: ["olympics", "sports", "1900s", "true history"],
    safety: "Real, documented event (1904 Olympic marathon, St. Louis). Comic tone at the expense of the organizers, whose choices caused the chaos; the strychnine 'doping' is framed as the dangerous medical ignorance it was.",
    hooks: [
      "The 1904 Olympic marathon was so cursed the winner crossed the line on rat poison. Documented.",
      "One water stop. 90-degree heat. Dust clouds from cars. The Olympics designed a disaster on purpose.",
      "The first man across the finish line did 11 miles of the marathon in a car. He almost got the gold."
    ],
    beats: [
      "St. Louis, August 1904. Thirty-two men line up for the Olympic marathon in 90-degree heat, on dust roads where officials' cars drive AHEAD of the runners, kicking grit into their lungs. The race organizer has deliberately kept water scarce — he wants to study dehydration. This is the starting point.",
      "First across the line is American Fred Lorz, fresh as a daisy — because after cramping at mile nine, he'd hopped into a car for eleven miles, waved at spectators from the passenger seat, then jogged the rest. He's nearly crowned before the truth lands. His defense: it was a joke.",
      "The real leader, Thomas Hicks, is meanwhile being kept upright by his handlers with the cutting-edge sports science of 1904: doses of strychnine — yes, the rat poison, then used as a stimulant — mixed with brandy and egg whites. He hallucinates, begs to lie down, and is all but carried across the line. He wins.",
      "Further back, Cuban postman Félix Carvajal — racing in cut-down trousers after losing his money on the way to St. Louis — chats with spectators, detours into an orchard for some apples that turn out to be bad, stops for a nap to settle his stomach... and STILL finishes fourth. Also on the course: Len Taunyane of South Africa, chased nearly a mile off route by aggressive dogs. He finishes ninth.",
      "Of thirty-two starters, fourteen finish, and the near-fatal shambles forces the Olympics to take marathons seriously — water, supervision, actual rules. Every marathon aid station you've ever seen is, in a way, an apology for St. Louis 1904."
    ],
    shotList: [
      "Hook: sepia archival look of runners in 1900s singlets disappearing into a dust cloud kicked up by an early automobile on a dirt road.",
      "A grinning athlete waving from the passenger seat of a 1904 open-top car while exhausted runners plod behind.",
      "Two handlers in flat caps supporting a glassy-eyed runner between them, one holding a brandy bottle and a spoon.",
      "A small mustachioed runner in cut-off trousers asleep under an orchard tree, apples scattered, race number still pinned on.",
      "A runner sprinting off a country road with two farm dogs at his heels, wheat fields, period photograph texture.",
      "Closer: a battered 1904 gold medal on a wooden table next to an antique brown medicine bottle, single overhead light."
    ],
    captions: [
      "St. Louis 1904: the marathon that had everything except water. 🏃",
      "Winner: strychnine and brandy. Runner-up story: a mid-race nap. Fourth place.",
      "Every aid station is an apology for this race."
    ],
    thumbnails: [
      "THE CURSED MARATHON",
      "Rat poison at mile 20",
      "He napped. Came 4th."
    ]
  },
  {
    id: "th-wojtek",
    category: "True History",
    title: "The bear who served in the army",
    image: { glyph: "🐻", from: "#3d2f1a", to: "#2d8a6e" },
    premise: "Wojtek was a Syrian brown bear bought as a cub by Polish soldiers in 1942. To get him aboard a troop ship, they enlisted him — rank: private. At Monte Cassino he carried crates of artillery shells through an active battle. His unit put him on their badge. All of it is true.",
    tags: ["ww2", "animals", "poland", "true history"],
    safety: "Real, documented story (Wojtek, 22nd Artillery Supply Company, Polish II Corps). Wartime setting handled respectfully; focuses on the soldiers' bond with the bear, no combat gore.",
    hooks: [
      "In WWII, the Polish army enlisted a bear. Rank: private. Job: carrying artillery shells. True story.",
      "The troop ship said soldiers only. So they made the bear a soldier.",
      "There's a WWII unit whose official badge is a bear carrying an artillery shell. Here's why."
    ],
    beats: [
      "Iran, 1942. Polish soldiers newly released from Soviet camps are trekking toward the front when they meet a boy with an orphaned bear cub. They trade him food and a pocket knife for it. The cub rides in a supply truck, is raised on condensed milk from a vodka bottle, and gets a name: Wojtek — 'happy warrior.'",
      "Wojtek grows into a 200-kilo soldier's mascot who wrestles the men, rides shotgun in trucks, drinks the occasional beer ration, and — his one bad habit — eats cigarettes. When the unit ships out for Italy in 1944, the port's rule is firm: no mascots, personnel only. So the Polish II Corps formally enlists him. Private Wojtek now has a rank, a paybook, and a place on the manifest.",
      "Then comes Monte Cassino, one of the war's most brutal battles. Ammunition has to move uphill under fire, crate after crate. Witnesses from his company describe Wojtek watching the men, then standing up, holding out his forearms — and spending the battle carrying heavy crates of shells alongside them. The unit swears he never dropped one.",
      "His company is so proud that they redesign their official emblem: a bear carrying an artillery shell. It goes on their trucks, their uniforms, their letters. Wojtek is promoted to corporal — genuinely on the books of the 22nd Artillery Supply Company.",
      "After the war, Wojtek retires to Edinburgh Zoo, where old Polish comrades visit for decades — calling to him in Polish, tossing him the odd cigarette over the fence, some say jumping in for a wrestle. Statues of him now stand in Edinburgh and Kraków: a private, a corporal, and by every account, a good soldier."
    ],
    shotList: [
      "Hook: archival-style shot of a brown bear standing upright among smiling WWII soldiers in field uniforms beside a supply truck.",
      "Warm dusty scene: young soldiers bottle-feeding a small bear cub from a glass bottle at a desert camp, mountains behind.",
      "A grown bear seated in the back of an open army truck among kit bags, soldiers laughing, Mediterranean coast road.",
      "Dramatic hillside: the bear upright, forearms wrapped around a wooden ammunition crate, soldiers hauling crates alongside, smoke on the ridge.",
      "Close-up: a painted unit emblem on a truck door — a bear carrying an artillery shell — weathered and chipped.",
      "Closer: the bronze statue of Wojtek in Edinburgh's Princes Street Gardens, an old man in a beret resting a hand on its paw."
    ],
    captions: [
      "Private Wojtek: enlisted 1944, promoted to corporal, never dropped a crate. 🐻",
      "The port said soldiers only. So the bear became a soldier.",
      "His unit's badge is still a bear carrying a shell."
    ],
    thumbnails: [
      "PRIVATE BEAR",
      "He enlisted in 1944",
      "Never dropped a crate"
    ]
  },

  /* ---------------- USER-REQUESTED TEST SCENARIOS ---------------- */
  {
    id: "pc-remote",
    category: "Pop Culture",
    title: "What if the TV remote was never invented?",
    image: { glyph: "📺", from: "#3a6ea5", to: "#151a30" },
    premise: "The gadget lost in your couch cushions quietly rewired how the whole world watches TV. Take it away and you don't just stand up more — you might erase the binge, the skippable ad, and the attention economy in your living room.",
    tags: ["tech", "tv", "everyday", "alternate history"],
    safety: "Light alternate-history speculation grounded in real TV and remote-control history.",
    hooks: [
      "What if you had to stand up every single time you wanted to change the channel?",
      "The gadget in your couch cushion quietly rewired how the entire planet watches TV.",
      "No remote means no channel surfing — and no channel surfing might mean no attention economy."
    ],
    beats: [
      "Picture the before-times: you walk up to the TV and twist a dial. Game consoles with the buttons on the box itself. Getting off the couch just to skip a boring part. For decades, that was watching TV.",
      "The remote didn't just save you steps — it invented channel surfing. Suddenly boredom cost one thumb-press, and TV had to fight for your attention every single second or lose you to the next channel.",
      "Kill the remote and that pressure never exists. Shows can breathe, ads can't be thumb-skipped, and 'appointment TV' — everyone watching the same thing at 8pm — stays king for decades longer.",
      "Here's the ripple: streaming's autoplay, the '5…4…3…' next-episode countdown, the engineered binge — they're all descendants of remote-era attention warfare. No remote, maybe no binge.",
      "Payoff: the remote looks like the laziest invention ever made. It was actually the starting gun for the war over your attention — and it was fired from your own couch."
    ],
    shotList: [
      "INTRO MONTAGE — rapid cuts under the hook, one example per second: (1) a hand pressing a modern TV remote; (2) someone getting up and walking to a boxy old TV to twist the channel dial; (3) close-up of a retro game console with the buttons on the unit itself; (4) a kid being told 'change it for me' and trudging to the set.",
      "Tight on fingers turning an old dial-TV knob, satisfying mechanical click.",
      "Split screen: a couch potato thumb-surfing 200 channels vs a family sitting still through one program.",
      "Ad graphic: a 'SKIP' thumb-button crossed out, then a person walking to the kitchen instead of skipping.",
      "Streaming UI mockup: the autoplay '5…4…3…' countdown, labeled 'built by the remote'.",
      "Closer: the remote alone on a couch cushion, slow push-in, single caption line."
    ],
    captions: [
      "The remote didn't make us lazy. It started a war for your attention. 📺",
      "No remote = no channel surfing = a very different internet.",
      "The most powerful gadget in your house is lost in the couch cushions."
    ],
    thumbnails: [
      "NO REMOTE?",
      "It started a war",
      "Get UP to change it"
    ]
  },
  {
    id: "sc-volcano",
    category: "Science",
    title: "What if every country had an active volcano?",
    image: { glyph: "🌋", from: "#b8563a", to: "#151a30" },
    premise: "Most countries have zero active volcanoes and a handful have dozens. Hand every nation on Earth its own live volcano and the world's farmland, power grid, and disaster maps all get redrawn overnight.",
    tags: ["geology", "earth", "volcanoes", "thought experiment"],
    safety: "Geology thought experiment — real volcano science, an impossible even distribution. Volcanic disasters are real; keep the tone curious, never gleeful.",
    hooks: [
      "Most countries don't have a single active volcano. What if every one of them did?",
      "A volcano in the Netherlands. One in Singapore. One in the middle of the desert. Now what?",
      "Give every country a volcano and you've handed each one a free farm, a free power plant, and a countdown timer."
    ],
    beats: [
      "The reality first: active volcanoes cluster on plate boundaries — the Ring of Fire, mostly. Huge regions like inland Africa, Australia, Northern Europe, and the Gulf states have essentially none.",
      "Now drop one live volcano in every country. Instantly you've invented new mountains, new fields of lava rock, and new national landmarks in places that were board-flat yesterday.",
      "The gift nobody expects: volcanic soil is some of the most fertile on Earth, and the heat underneath is free power. Iceland already runs its whole grid on volcanic geothermal — now every country can.",
      "The bill: every capital now needs eruption monitoring, evacuation plans, and airspace its own volcano can shut down with a single ash cloud. Free energy, permanent anxiety.",
      "Payoff: a volcano is the most honest neighbor a country could have. It will make your soil rich and your power cheap — and one day, on a schedule it never shares, it will try to bury you."
    ],
    shotList: [
      "Hook: spinning globe where a glowing volcano icon pops up on every single country, one after another.",
      "Map: the real Ring of Fire lit up, then the 'empty' continents highlighted with 'zero active volcanoes'.",
      "Before/after: a flat, famous skyline (desert city or lowland) with a brand-new volcano rising behind it.",
      "Split: lush volcanic farmland beside a geothermal plant venting steam, labeled 'the upside'.",
      "Ash-cloud animation grounding planes over a country, labeled 'the bill'.",
      "Closer: a calm village at the foot of a gently smoking volcano at dusk, one caption line."
    ],
    captions: [
      "Most countries have zero active volcanoes. Imagine if every one had its own. 🌋",
      "A volcano is a free farm, a free power plant, and a countdown timer.",
      "The most honest neighbor a country could ask for."
    ],
    thumbnails: [
      "A VOLCANO PER COUNTRY",
      "Free power. Real risk.",
      "Every flag gets a volcano"
    ]
  },
  {
    id: "sc-evolve",
    category: "Science",
    title: "What if humans evolved for a million years of total automation?",
    image: { glyph: "🧬", from: "#2d8a6e", to: "#5a4a7a" },
    premise: "Robots build everything, AI does the thinking, and nobody lifts a finger — for a million years. Everyone pictures soft, shrunken blobs. The real evolutionary answer is stranger, and it ends with the pencil in our own hands.",
    tags: ["evolution", "biology", "future", "ai"],
    safety: "Speculative evolutionary biology — grounded in real principles (selection needs pressure), clearly framed as far-future imagination.",
    hooks: [
      "A million years of robots doing everything. What do humans evolve into? Your first guess is probably wrong.",
      "Everyone imagines we'd melt into soft little blobs. Evolution says: not so fast.",
      "If AI thinks for us for a million years, do our brains shrink? The honest answer is unsettling."
    ],
    beats: [
      "The picture everyone has: robots do the lifting, AI does the thinking, so humans go soft — short weak limbs, stubby fingers, big lazy heads. Little balls with a face. The classic sci-fi blob.",
      "Here's the catch: you don't lose your legs just from sitting. A trait only disappears if having it costs you children. Comfort removes that pressure — which slows evolution down, it doesn't melt us into blobs.",
      "So what actually changes? The things that still cost us. We already have smaller jaws and crowded teeth from soft cooked food — run that a million years and faces keep shrinking. And if medicine keeps everyone reproducing, we get more varied, not more uniform.",
      "Now the wildcard: the moment we let tech choose our mates, edit our genes, or grow bodies to order, evolution stops being natural at all. We'd redesign ourselves in centuries — something blind evolution needs millions of years to do.",
      "Payoff: we won't drift into stubby little balls by accident — that only happens if being a ball helps you have more kids. The real future is scarier and cooler: for the first time, the species doing the evolving is holding the pencil."
    ],
    shotList: [
      "Hook: morph animation of a human slowly rounding into the 'sci-fi blob' — big head, tiny limbs, stubby fingers — with a cheeky 'what everyone pictures' stamp.",
      "Record-scratch cut to a clean diagram: 'disuse ≠ disappearance', a trait needing 'selection pressure' to vanish.",
      "Before/after skulls: a modern jaw vs a smaller future jaw with crowded teeth, 'already happening' label.",
      "Branching graphic: one population splitting into many varied body types instead of one uniform blob.",
      "The wildcard: a DNA strand being edited by a cursor while robots assemble a body in the background.",
      "Closer: a hand holding a pencil over a blank human silhouette, drawing the next version; one caption line."
    ],
    captions: [
      "We won't evolve into little blobs by accident. The truth is weirder. 🧬",
      "Disuse doesn't delete a body part — only losing kids over it does.",
      "For the first time, the species doing the evolving is holding the pencil."
    ],
    thumbnails: [
      "BLOB HUMANS? NO.",
      "1,000,000 years of AI",
      "We hold the pencil now"
    ]
  }
];

/* ============================================================
   3. SEED BANK — New Scenario Seed rotation, all categories
   ============================================================ */

const seedBank = {
  "Speculative": [
    "What if gravity took one day off every year?",
    "What if sleep became optional — for a price?",
    "What if everyone's lifespan was public information?",
    "What if the oceans were freshwater?"
  ],
  "Science": [
    "What if Earth had rings like Saturn?",
    "What if the speed of light were 100 km/h?",
    "What if we could photograph a dream?",
    "What if a new ice age started this decade?"
  ],
  "History": [
    "What if the printing press arrived 1,000 years earlier?",
    "What if the Roman Empire had industrialized?",
    "What if the Silk Road never opened?",
    "What if the moon landing had been the second one?"
  ],
  "Pop Culture": [
    "What if one-hit wonders were legally required to make a second hit?",
    "What if video games had been invented before movies?",
    "What if celebrities had to publish their search history once a year?",
    "What if every canceled show got one crowd-written finale?"
  ],
  "Internet Mystery": [
    "What if a dead website updated one more time?",
    "What if your spam folder was sorting messages correctly?",
    "What if a livestream had been running since 2007 and nobody knew who started it?",
    "What if a captcha ever said no — permanently?"
  ],
  "Alternate Reality": [
    "What if you woke up left-handed in a left-handed world?",
    "What if your dreams were someone else's memories?",
    "What if yesterday quietly happened twice?",
    "What if every door you never opened led somewhere new now?"
  ],
  "Unsettling Everyday": [
    "What if elevators kept a log of everything said inside them?",
    "What if flickering streetlights were counting you?",
    "What if your handwriting slowly stopped being yours?",
    "What if the last photo in your camera roll wasn't taken by you?"
  ],
  "Scary/Weird": [
    "What if the static between radio stations was never empty?",
    "What if hibernation was contagious?",
    "What if a lighthouse kept running with no keeper — and no bill?",
    "What if your name sounded different to everyone who says it?"
  ],
  "Scary Story": [
    "The dive log that ends mid-sentence",
    "A ranger's list of things you don't do after dark",
    "The apartment above yours that isn't on the lease",
    "Every photo of the lake house has one extra window",
    "The night bus that makes one extra stop",
    "The babysitter's note: he's already asleep, don't check",
    "The storage unit paid up forty years in advance",
    "Mile markers on a highway that doesn't exist",
    "The voicemail your own number keeps leaving you",
    "A lighthouse logbook with two sets of handwriting",
    "The elevator stops at a floor the building doesn't have",
    "The trail cameras only ever catch it leaving"
  ],
  "True History": [
    "The war two cities fought over a wooden bucket",
    "The wave of molasses that ran faster than a man",
    "The tree that legally owns itself",
    "The shortest war in history lasted 38 minutes",
    "The soldier who kept fighting WWII until 1974",
    "The pig that nearly started a US-British war",
    "The parachuting beavers of Idaho",
    "1816: the year without a summer",
    "Operation Paul Bunyan: an army versus one tree",
    "The London bridge that was sold to Arizona",
    "The cat that co-authored a physics paper",
    "The tulips that cost more than houses"
  ]
};

/* ============================================================
   4. STORAGE — localStorage with in-memory fallback (file://)
   ============================================================ */

const storage = (() => {
  let mode = "local";
  let memory = {};
  try {
    const probe = "__wis_probe__";
    window.localStorage.setItem(probe, "1");
    window.localStorage.removeItem(probe);
  } catch (err) {
    mode = "memory";
  }
  return {
    get mode() { return mode; },
    read() {
      try {
        if (mode === "local") {
          const raw = window.localStorage.getItem(STORAGE_KEY);
          return raw ? JSON.parse(raw) : null;
        }
        return memory[STORAGE_KEY] || null;
      } catch (err) {
        return null;
      }
    },
    write(data) {
      try {
        if (mode === "local") {
          window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        } else {
          memory[STORAGE_KEY] = data;
        }
      } catch (err) {
        // Quota or privacy failure mid-session: degrade to memory.
        mode = "memory";
        memory[STORAGE_KEY] = data;
        renderStorageBadge();
      }
    },
    clear() {
      try {
        if (mode === "local") window.localStorage.removeItem(STORAGE_KEY);
      } catch (err) { /* ignore */ }
      memory = {};
    }
  };
})();

/* ============================================================
   5. STATE
   ============================================================ */

const state = {
  search: "",
  category: "All",
  selectedId: null,
  options: { runtime: 60, voice: "calm" },
  pkg: null,
  activeTab: 0,
  seed: null,
  seedRotation: { catIndex: 0, perCat: {} },
  customScenarios: []
};

function persist() {
  storage.write({
    seedRotation: state.seedRotation,
    customScenarios: state.customScenarios
  });
}

function restore() {
  const saved = storage.read();
  if (!saved) return;
  if (saved.seedRotation && typeof saved.seedRotation.catIndex === "number") {
    state.seedRotation = {
      catIndex: saved.seedRotation.catIndex % CATEGORIES.length,
      perCat: saved.seedRotation.perCat || {}
    };
  }
  if (Array.isArray(saved.customScenarios)) {
    state.customScenarios = saved.customScenarios.filter(s =>
      s && typeof s.id === "string" && typeof s.title === "string" && Array.isArray(s.beats));
  }
}

function allScenarios() {
  return scenarioBank.concat(state.customScenarios);
}

/* ============================================================
   6. DOM HELPERS
   ============================================================ */

const $ = (id) => document.getElementById(id);

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  for (const child of children) node.appendChild(child);
  return node;
}

/* Collapsible sidebar state (plain localStorage: UI pref, not app data). */
function setNavCollapsed(collapsed, persist = true) {
  document.body.classList.toggle("nav-collapsed", collapsed);
  const toggle = $("navToggle");
  if (toggle) {
    toggle.setAttribute("aria-expanded", String(!collapsed));
    toggle.setAttribute("aria-label", collapsed ? "Expand menu" : "Collapse menu");
  }
  if (persist) {
    try { window.localStorage.setItem("wis.navCollapsed", collapsed ? "1" : "0"); } catch (err) { /* ignore */ }
  }
}

let statusTimer = null;
function announce(message) {
  const box = $("actionStatus");
  if (!box) return;
  box.textContent = message;
  clearTimeout(statusTimer);
  statusTimer = setTimeout(() => { box.textContent = ""; }, 4000);
}

/* Roving-tabindex arrow-key navigation for radiogroups and tablists. */
function bindArrowNav(container, itemSelector, onMove) {
  container.addEventListener("keydown", (event) => {
    const keys = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"];
    if (!keys.includes(event.key)) return;
    const items = Array.from(container.querySelectorAll(itemSelector));
    if (!items.length) return;
    const current = items.indexOf(document.activeElement);
    let next = current < 0 ? 0 : current;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") next = (current + 1) % items.length;
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = (current - 1 + items.length) % items.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = items.length - 1;
    event.preventDefault();
    items[next].focus();
    onMove(items[next]);
  });
}

/* ============================================================
   7. LIBRARY RENDERING
   ============================================================ */

function filteredScenarios() {
  const query = state.search.trim().toLowerCase();
  return allScenarios().filter(s => {
    if (state.category !== "All" && s.category !== state.category) return false;
    if (!query) return true;
    const haystack = [s.title, s.premise, s.category, ...s.tags].join(" ").toLowerCase();
    return query.split(/\s+/).every(word => haystack.includes(word));
  });
}

function renderCategoryChips() {
  const wrap = $("categoryChips");
  wrap.innerHTML = "";
  const options = ["All", ...CATEGORIES];
  options.forEach(cat => {
    const selected = state.category === cat;
    const chip = el("button", {
      type: "button",
      class: "chip",
      role: "radio",
      "aria-checked": String(selected),
      tabindex: selected ? "0" : "-1",
      text: cat,
      onclick: () => { state.category = cat; renderCategoryChips(); renderLibrary(); }
    });
    wrap.appendChild(chip);
  });
}

/* One-click "render the whole category": shown while a category filter is
   active; exports a single multi-slot queue the watcher renders in one run. */
function renderBatchRow() {
  const row = $("batchRenderRow");
  if (!row) return;
  row.innerHTML = "";
  const cat = state.category;
  const n = cat === "All" ? 0 : allScenarios().filter(s => s.category === cat).length;
  row.hidden = !n;
  if (!n) return;
  row.appendChild(el("button", {
    type: "button",
    class: "btn btn-wide",
    text: `🎬 Render all ${n} ${cat} scenario${n === 1 ? "" : "s"}`,
    onclick: () => {
      if (!confirm(`Export all ${n} ${cat} scenario${n === 1 ? "" : "s"} as one render queue?\nThe watcher renders them back-to-back — a few minutes each, free.`)) return;
      exportCategoryForRender(cat);
      announce(`Exported ${n} ${cat} package${n === 1 ? "" : "s"} in one queue — the watcher takes it from here.`);
    }
  }));
}

function renderLibrary() {
  const grid = $("scenarioGrid");
  grid.innerHTML = "";
  const matches = filteredScenarios();
  $("libraryCount").textContent = `${matches.length} of ${allScenarios().length} scenarios`;
  $("libraryEmpty").hidden = matches.length > 0;
  renderBatchRow();

  matches.forEach(s => {
    const card = el("button", {
      type: "button",
      class: "scenario-card" + (s.id === state.selectedId ? " selected" : ""),
      "aria-pressed": String(s.id === state.selectedId),
      onclick: () => selectScenario(s.id)
    });
    const glyph = el("span", { class: "card-glyph", "aria-hidden": "true", text: s.image.glyph });
    glyph.style.background = `linear-gradient(135deg, ${s.image.from}, ${s.image.to})`;
    const top = el("div", { class: "card-top" }, [
      glyph,
      el("span", { class: "category-badge", text: s.category })
    ]);
    if (s.custom) top.appendChild(el("span", { class: "custom-flag", text: "Custom" }));
    const title = el("p", { class: "card-title", text: s.title });
    const tags = el("div", { class: "tag-row" }, s.tags.slice(0, 3).map(t => el("span", { class: "tag", text: t })));
    card.append(top, title, tags);
    const item = el("div", { role: "listitem" }, [card]);
    grid.appendChild(item);
  });
}

/* ============================================================
   8. WORKSPACE
   ============================================================ */

function selectScenario(id) {
  state.selectedId = id;
  state.pkg = null;
  $("packageSection").hidden = true;
  renderLibrary();
  renderWorkspace();
  const banner = $("bannerTitle");
  if (banner) banner.focus?.();
}

function getScenario(id) {
  return allScenarios().find(s => s.id === id) || null;
}

function renderWorkspace() {
  const scenario = getScenario(state.selectedId);
  $("workspaceEmpty").hidden = Boolean(scenario);
  $("workspaceBody").hidden = !scenario;
  if (!scenario) return;

  const glyph = $("bannerGlyph");
  glyph.textContent = scenario.image.glyph;
  glyph.style.background = `linear-gradient(135deg, ${scenario.image.from}, ${scenario.image.to})`;
  $("bannerCategory").textContent = scenario.category + (scenario.custom ? " · Custom" : "");
  $("bannerTitle").textContent = scenario.title;
  $("deleteScenarioBtn").hidden = !scenario.custom;
  $("bannerPremise").textContent = scenario.premise;
  $("bannerSafety").textContent = "Framing note: " + scenario.safety;

  const tagRow = $("bannerTags");
  tagRow.innerHTML = "";
  scenario.tags.forEach(t => tagRow.appendChild(el("span", { class: "tag", text: t })));

  renderRuntimeControl();

  const voiceSelect = $("voiceSelect");
  voiceSelect.innerHTML = "";
  VOICES.forEach(v => voiceSelect.appendChild(el("option", { value: v.id, text: v.label })));
  voiceSelect.value = state.options.voice;
}

/* Runtime is picked in two places (Package Settings and the builder dialog) -
   both write state.options.runtime and re-sync the other control. */
function renderRuntimeControl() {
  renderSegmented($("runtimeGroup"), RUNTIMES.map(r => ({ value: String(r.id), label: r.label })), String(state.options.runtime), v => {
    state.options.runtime = Number(v);
    syncBuilderRuntime();
  });
}

function syncBuilderRuntime() {
  const sel = $("bRuntime");
  if (sel && sel.options.length) sel.value = String(state.options.runtime);
}

function renderSegmented(container, items, activeValue, onPick) {
  container.innerHTML = "";
  items.forEach(item => {
    const selected = item.value === activeValue;
    container.appendChild(el("button", {
      type: "button",
      class: "segment",
      role: "radio",
      "aria-checked": String(selected),
      tabindex: selected ? "0" : "-1",
      "data-value": item.value,
      text: item.label,
      onclick: () => {
        onPick(item.value);
        renderSegmented(container, items, item.value, onPick);
      }
    }));
  });
}

/* ============================================================
   9. PACKAGE BUILDER
   ============================================================ */

function buildPackage(scenario, options) {
  const runtime = RUNTIMES.find(r => r.id === options.runtime) || RUNTIMES[1];
  const voice = VOICES.find(v => v.id === options.voice) || VOICES[0];

  const beats = scenario.beats.slice(0, runtime.beats);
  const cta = CATEGORY_CTA[scenario.category] || NEUTRAL_CTA;
  const hypeLead = HYPE_LEAD[scenario.category] || "That's the timeline — tell me where it breaks.";
  const outro = voice.id === "hype"
    ? `${hypeLead} ${cta}`
    : voice.id === "deadpan"
      ? `Anyway. ${cta}`
      : `Sit with that one for a second. ${cta}`;

  // Captions stay clean; the render's post kit adds hashtags per platform.
  const captions = scenario.captions.slice();

  return {
    scenarioId: scenario.id,
    title: scenario.title,
    category: scenario.category,
    colors: { from: scenario.image.from, to: scenario.image.to },
    platform: "Any",
    aspect: ASPECT,
    runtime: runtime.id,
    runtimeLabel: runtime.label,
    pacingNote: runtime.note,
    voice: voice.label,
    direction: voice.direction,
    premise: scenario.premise,
    safety: scenario.safety,
    hooks: scenario.hooks.slice(),
    beats,
    outro,
    shotList: scenario.shotList.slice(),
    captions,
    thumbnails: scenario.thumbnails.slice(),
    generatedAt: new Date().toISOString()
  };
}

function packageToText(pkg) {
  const lines = [];
  lines.push("WHAT IF STUDEOS — CONTENT PACKAGE");
  lines.push("=".repeat(40));
  lines.push(`Title:     ${pkg.title}`);
  lines.push(`Category:  ${pkg.category}`);
  lines.push(`Format:    ${pkg.aspect} — works on TikTok, YT Shorts, and Reels`);
  lines.push(`Runtime:   ${pkg.runtimeLabel}`);
  lines.push(`Voice:     ${pkg.voice}`);
  lines.push(`Generated: ${pkg.generatedAt}`);
  lines.push("");
  lines.push("PREMISE");
  lines.push(pkg.premise);
  lines.push("");
  lines.push("SAFETY / FRAMING");
  lines.push(pkg.safety);
  lines.push("");
  lines.push("HOOK OPTIONS (pick one)");
  pkg.hooks.forEach((h, i) => lines.push(`${i + 1}. ${h}`));
  lines.push("");
  lines.push(`SCRIPT BEATS — ${pkg.runtimeLabel}`);
  lines.push(`(Pacing: ${pkg.pacingNote})`);
  pkg.beats.forEach((b, i) => lines.push(`${i + 1}. ${b}`));
  lines.push(`Outro: ${pkg.outro}`);
  lines.push("");
  lines.push("VOICE DIRECTION");
  lines.push(pkg.direction);
  lines.push("");
  lines.push("SHOT LIST");
  pkg.shotList.forEach((s, i) => lines.push(`${i + 1}. ${s}`));
  lines.push("");
  lines.push("CAPTION OPTIONS");
  pkg.captions.forEach((c, i) => lines.push(`${i + 1}. ${c.replace(/\n/g, "  |  ")}`));
  lines.push("");
  lines.push("THUMBNAIL / TITLE-CARD TEXT");
  pkg.thumbnails.forEach((t, i) => lines.push(`${i + 1}. "${t}"`));
  lines.push("");
  lines.push("-".repeat(40));
  lines.push("Made with What If Studeos (local, offline). Content is speculative fiction / thought experiment.");
  return lines.join("\n");
}

/* ---------- SRT ---------- */

function formatSrtTime(totalMs) {
  const ms = Math.max(0, Math.round(totalMs));
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  const rem = ms % 1000;
  const pad = (n, w = 2) => String(n).padStart(w, "0");
  return `${pad(h)}:${pad(m)}:${pad(s)},${pad(rem, 3)}`;
}

/* Split a long line into subtitle-sized chunks (~9 words). */
function chunkLine(text, maxWords = 9) {
  const words = text.split(/\s+/);
  const chunks = [];
  for (let i = 0; i < words.length; i += maxWords) {
    chunks.push(words.slice(i, i + maxWords).join(" "));
  }
  return chunks;
}

function packageToSrt(pkg) {
  const totalMs = pkg.runtime * 1000;
  const lines = [pkg.hooks[0], ...pkg.beats, pkg.outro];
  const chunks = lines.flatMap(line => chunkLine(line));
  const weights = chunks.map(c => Math.max(c.split(/\s+/).length, 2));
  const weightSum = weights.reduce((a, b) => a + b, 0);

  let cursor = 0;
  const cues = [];
  chunks.forEach((chunk, i) => {
    const dur = (weights[i] / weightSum) * totalMs;
    const start = cursor;
    const end = i === chunks.length - 1 ? totalMs : cursor + dur;
    cues.push(`${i + 1}\n${formatSrtTime(start)} --> ${formatSrtTime(end)}\n${chunk}\n`);
    cursor = end;
  });
  return cues.join("\n");
}

/* ============================================================
   10. PACKAGE RENDERING (tabs)
   ============================================================ */

const TAB_DEFS = [
  { id: "hooks", label: "Hooks" },
  { id: "beats", label: "Script Beats" },
  { id: "shots", label: "Shot List" },
  { id: "captions", label: "Captions" },
  { id: "thumbs", label: "Thumbnails" },
  { id: "safety", label: "Safety & Notes" }
];

function tabContent(pkg, tabId) {
  switch (tabId) {
    case "hooks":
      return {
        html: `<h5>Hook options — pick one, say it in the first 2 seconds</h5><ol>${pkg.hooks.map(h => `<li>${escapeHtml(h)}</li>`).join("")}</ol>`,
        text: pkg.hooks.map((h, i) => `${i + 1}. ${h}`).join("\n")
      };
    case "beats":
      return {
        html: `<h5>Script beats — ${escapeHtml(pkg.runtimeLabel)}</h5><p>${escapeHtml(pkg.pacingNote)}</p><ol>${pkg.beats.map(b => `<li>${escapeHtml(b)}</li>`).join("")}</ol><h5>Outro</h5><p>${escapeHtml(pkg.outro)}</p><h5>Voice direction — ${escapeHtml(pkg.voice)}</h5><p>${escapeHtml(pkg.direction)}</p>`,
        text: [`Pacing: ${pkg.pacingNote}`, ...pkg.beats.map((b, i) => `${i + 1}. ${b}`), `Outro: ${pkg.outro}`, `Voice direction: ${pkg.direction}`].join("\n")
      };
    case "shots":
      return {
        html: `<h5>Shot list — ${escapeHtml(pkg.aspect)}</h5><ol>${pkg.shotList.map(s => `<li>${escapeHtml(s)}</li>`).join("")}</ol>`,
        text: pkg.shotList.map((s, i) => `${i + 1}. ${s}`).join("\n")
      };
    case "captions":
      return {
        html: `<h5>Caption options</h5><p>Per-platform hashtags are added in the rendered video's post kit.</p><ol>${pkg.captions.map(c => `<li>${escapeHtml(c).replace(/\n/g, "<br>")}</li>`).join("")}</ol>`,
        text: pkg.captions.map((c, i) => `${i + 1}. ${c}`).join("\n\n")
      };
    case "thumbs":
      return {
        html: `<h5>Thumbnail / title-card text</h5><ul>${pkg.thumbnails.map(t => `<li>“${escapeHtml(t)}”</li>`).join("")}</ul>`,
        text: pkg.thumbnails.map((t, i) => `${i + 1}. "${t}"`).join("\n")
      };
    case "safety":
      return {
        html: `<h5>Safety / framing</h5><p>${escapeHtml(pkg.safety)}</p><h5>Publishing notes</h5><p>Label speculation as speculation on screen where the audience might mistake it for fact. This package is a starting script — record it in your own words. Publishing and platform rules are your responsibility; nothing here automates posting or promises performance.</p>`,
        text: `Safety / framing: ${pkg.safety}\n\nPublishing notes: label speculation as speculation on screen where the audience might mistake it for fact. This package is a starting script — record it in your own words. Publishing and platform rules are your responsibility; nothing here automates posting or promises performance.`
      };
    default:
      return { html: "", text: "" };
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderPackage() {
  const pkg = state.pkg;
  const section = $("packageSection");
  if (!pkg) { section.hidden = true; return; }
  section.hidden = false;

  $("packageTitle").textContent = "Package: " + pkg.title;
  $("packageMeta").textContent = `${pkg.aspect} · ${pkg.runtimeLabel} · ${pkg.voice}`;

  const tabsWrap = $("packageTabs");
  tabsWrap.innerHTML = "";
  TAB_DEFS.forEach((tab, index) => {
    const selected = index === state.activeTab;
    tabsWrap.appendChild(el("button", {
      type: "button",
      class: "tab",
      role: "tab",
      id: `tab-${tab.id}`,
      "aria-selected": String(selected),
      "aria-controls": "tabPanel",
      tabindex: selected ? "0" : "-1",
      text: tab.label,
      onclick: () => { state.activeTab = index; renderPackage(); }
    }));
  });

  const panel = $("tabPanel");
  const active = TAB_DEFS[state.activeTab];
  panel.setAttribute("aria-labelledby", `tab-${active.id}`);
  panel.innerHTML = tabContent(pkg, active.id).html;
}

/* ============================================================
   11. EXPORT FOR RENDER (one-item queue format - the watcher,
   Produce page, and pipeline all consume this shape unchanged)
   ============================================================ */

function exportForRender(pkg) {
  const payload = {
    app: "what-if-studio", format: 1, exportedAt: new Date().toISOString(),
    items: [{ slot: 1, status: "planned", notes: "", package: pkg }]
  };
  // "whatifstudio-" prefix is what the Downloads watcher looks for.
  downloadFile("whatifstudio-queue-" + slugify(pkg.title) + ".json", JSON.stringify(payload, null, 2));
}

/* Batch export: every scenario in a category becomes one slot of a single
   queue file, so the watcher renders the whole category back-to-back.
   Uses the current Package Settings (runtime + voice) for every package. */
function exportCategoryForRender(category) {
  const scenarios = allScenarios().filter(s => s.category === category);
  if (!scenarios.length) return 0;
  const payload = {
    app: "what-if-studio", format: 1, exportedAt: new Date().toISOString(),
    items: scenarios.map((s, i) => ({ slot: i + 1, status: "planned", notes: "", package: buildPackage(s, state.options) }))
  };
  downloadFile("whatifstudio-queue-" + slugify(category) + "-all.json", JSON.stringify(payload, null, 2));
  return scenarios.length;
}

/* ============================================================
   12. SEED ROTATION
   ============================================================ */

function nextSeed() {
  const rotation = state.seedRotation;
  const category = CATEGORIES[rotation.catIndex % CATEGORIES.length];
  const seeds = seedBank[category];
  const seedIndex = rotation.perCat[category] || 0;
  const seed = seeds[seedIndex % seeds.length];

  rotation.perCat[category] = (seedIndex + 1) % seeds.length;
  rotation.catIndex = (rotation.catIndex + 1) % CATEGORIES.length;

  state.seed = { category, text: seed };
  persist();

  $("seedText").textContent = `${category}: ${seed}`;
  $("copySeedBtn").disabled = false;
}

/* ============================================================
   13. CLIPBOARD + DOWNLOADS
   ============================================================ */

function copyText(text, label) {
  const fallback = () => {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.left = "-9999px";
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (err) { ok = false; }
    document.body.removeChild(area);
    announce(ok ? `${label} copied.` : "Copy failed — select and copy manually.");
  };

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text)
      .then(() => announce(`${label} copied.`))
      .catch(fallback);
  } else {
    fallback();
  }
}

function downloadFile(filename, content) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function slugify(text) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60) || "package";
}

/* ============================================================
   14. STORAGE BADGE + RESET
   ============================================================ */

function renderStorageBadge() {
  const badge = $("storageBadge");
  if (storage.mode === "local") {
    badge.textContent = "Saving locally on this device";
    badge.className = "storage-badge ok";
    badge.title = "Queue and notes persist in this browser's local storage. Nothing leaves your device.";
  } else {
    badge.textContent = "Memory only — export to keep work";
    badge.className = "storage-badge fallback";
    badge.title = "This browser blocks local storage for file:// pages. The app works, but the queue resets when you close the tab — use Export to keep packages.";
  }
}

function resetAll() {
  const ok = window.confirm("Reset ALL local data? This clears seed rotation and your custom scenarios. Exported files are not affected.");
  if (!ok) return;
  storage.clear();
  state.seedRotation = { catIndex: 0, perCat: {} };
  state.customScenarios = [];
  state.seed = null;
  state.pkg = null;
  state.selectedId = null;
  $("seedText").textContent = "Press the button to spin up a new scenario seed.";
  $("copySeedBtn").disabled = true;
  $("packageSection").hidden = true;
  renderLibrary();
  renderWorkspace();
  announce("All local data reset.");
}

/* ============================================================
   14b. CUSTOM SCENARIO BUILDER
   ============================================================ */

function firstSentence(text) {
  const match = String(text).match(/^[^.!?]*[.!?]?/);
  return (match ? match[0] : text).trim();
}

/* Turn the user's title/premise/beats into a complete scenario object.
   Hooks, captions, thumbnails, shot list, and safety framing are
   scaffolded from templates so everything downstream (queue, exports,
   pipeline AI visuals, music mood) works unchanged. */
function scaffoldScenario(input) {
  const rawTitle = input.title.trim().replace(/\s+/g, " ");
  const title = /\?$/.test(rawTitle) ? rawTitle : rawTitle + "?";
  const colors = CATEGORY_COLORS[input.category] || ["#6a5ae0", "#2dbf8b"];
  const stripped = title.replace(/^what if\s*/i, "").replace(/\?$/, "").trim();
  const keywords = stripped.split(/\s+/).slice(0, 5).join(" ").toUpperCase();
  const premise = input.premise.trim();
  const tags = input.tags.length ? input.tags.slice(0, 5) : [input.category.toLowerCase(), "thought experiment", "original"];

  return {
    id: "custom-" + slugify(title).slice(0, 40) + "-" + Date.now().toString(36),
    custom: true,
    category: input.category,
    title,
    image: { glyph: input.glyph || "✳️", from: colors[0], to: colors[1] },
    premise,
    tags,
    safety: "Original speculative scenario written by this channel — a fictional thought experiment, clearly framed as hypothetical, not a claim of fact.",
    hooks: [
      `${title} Here's what would actually happen.`,
      `Nobody asks this question — and the answer changes how you see the ordinary version.`,
      `${title} Stay with me, because the ending is not what you think.`
    ],
    beats: input.beats,
    shotList: [
      "Hook shot: a person face to camera, wide-eyed, teasing the question — " + firstSentence(premise),
      ...input.beats.map(b => "Reenactment: a person acting out this moment — " + firstSentence(b))
    ],
    captions: [
      title,
      "The answer is weirder than you expect.",
      "Watch to the end for the twist."
    ],
    thumbnails: [
      keywords || "WHAT IF",
      "NOBODY ASKS THIS",
      "WAIT FOR THE END"
    ]
  };
}

/* ---------- Optional AI draft ----------
   Fires only when the user clicks "Write it for me". The request goes through
   the local review dashboard (pipeline/review.bat), which writes with the
   OpenAI API when a key is configured (pipeline/openai_key.txt) and the free
   Pollinations API otherwise. Everything stays editable; the app works fine
   without it. */

const DRAFT_SERVICE = "http://127.0.0.1:8765/api/draft";

async function draftScenarioWithAI(title, category, runtime) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 90000);
  try {
    let response;
    try {
      response = await fetch(
        `${DRAFT_SERVICE}?title=${encodeURIComponent(title)}&category=${encodeURIComponent(category)}&runtime=${encodeURIComponent(runtime || 60)}`,
        { signal: controller.signal }
      );
    } catch (err) {
      throw new Error("dashboard-offline");
    }
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || "service error");
    const beats = (Array.isArray(data.beats) ? data.beats : [])
      .map(b => String(b).trim()).filter(Boolean).slice(0, 5);
    if (!data.premise || beats.length < 3) throw new Error("draft was incomplete");
    return {
      premise: String(data.premise).trim(),
      beats,
      engine: data.engine === "openai" ? "OpenAI" : "the free AI",
      tags: (Array.isArray(data.tags) ? data.tags : []).map(t => String(t).trim()).filter(Boolean).slice(0, 5),
      emoji: typeof data.emoji === "string" ? data.emoji.trim().slice(0, 4) : ""
    };
  } finally {
    clearTimeout(timer);
  }
}

function bindBuilder() {
  const dialog = $("builderDialog");
  const form = $("builderForm");
  const error = $("builderError");

  const categorySelect = $("bCategory");
  CATEGORIES.forEach(c => categorySelect.appendChild(el("option", { value: c, text: c })));

  const runtimeSelect = $("bRuntime");
  RUNTIMES.forEach(r => runtimeSelect.appendChild(el("option", { value: String(r.id), text: r.label })));
  runtimeSelect.addEventListener("change", () => {
    state.options.runtime = Number(runtimeSelect.value);
    renderRuntimeControl();   // keep Package Settings in step
  });

  const aiBtn = $("builderAiBtn");
  const aiStatus = $("builderAiStatus");
  const AI_HINT = "Type a title, and AI drafts the rest — you can edit everything.";

  $("newScenarioBtn").addEventListener("click", () => {
    form.reset();
    error.textContent = "";
    aiStatus.textContent = AI_HINT;
    syncBuilderRuntime();     // form.reset() clears the select; restore the current pick
    dialog.showModal();
    $("bTitle").focus();
  });

  $("builderCancel").addEventListener("click", () => dialog.close());

  aiBtn.addEventListener("click", async () => {
    const title = $("bTitle").value.trim();
    if (!title) {
      aiStatus.textContent = "Give it a title first — that's the idea the AI writes from.";
      $("bTitle").focus();
      return;
    }
    aiBtn.disabled = true;
    const rt = RUNTIMES.find(r => r.id === state.options.runtime);
    aiStatus.textContent = `Writing a ${rt ? rt.label : "60s"} draft… (a few seconds)`;
    try {
      const draft = await draftScenarioWithAI(title, categorySelect.value, state.options.runtime);
      // Fill only fields the user hasn't written in - never clobber their words.
      const kept = [];
      if (!$("bPremise").value.trim()) $("bPremise").value = draft.premise; else kept.push("premise");
      ["bBeat1", "bBeat2", "bBeat3", "bBeat4", "bBeat5"].forEach((id, i) => {
        if (!$(id).value.trim() && draft.beats[i]) $(id).value = draft.beats[i];
        else if ($(id).value.trim()) kept.push("beat " + (i + 1));
      });
      if (!$("bTags").value.trim() && draft.tags.length) $("bTags").value = draft.tags.join(", ");
      if (!$("bGlyph").value.trim() && draft.emoji) $("bGlyph").value = draft.emoji;
      aiStatus.textContent = kept.length
        ? `Draft by ${draft.engine} (kept your ${kept.slice(0, 3).join(", ")}${kept.length > 3 ? "…" : ""}). Edit anything, then add it.`
        : `Draft by ${draft.engine} — edit anything, then add it to your library.`;
    } catch (err) {
      aiStatus.textContent = err && err.message === "dashboard-offline"
        ? "The AI writer needs the Studio's helper running — double-click “Start-What-If-Studio” in the project folder once, then try again."
        : "The writing service hiccuped — try again in a moment, or fill it in yourself.";
    } finally {
      aiBtn.disabled = false;
    }
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const beats = ["bBeat1", "bBeat2", "bBeat3", "bBeat4", "bBeat5"]
      .map(id => $(id).value.trim())
      .filter(Boolean);
    const input = {
      title: $("bTitle").value,
      category: categorySelect.value,
      glyph: $("bGlyph").value.trim(),
      premise: $("bPremise").value,
      tags: $("bTags").value.split(",").map(t => t.trim()).filter(Boolean),
      beats
    };
    if (!input.title.trim()) { error.textContent = "Give it a title — the question is the video."; $("bTitle").focus(); return; }
    if (!input.premise.trim()) { error.textContent = "Add a premise — one to three sentences setting up the idea."; $("bPremise").focus(); return; }
    if (beats.length < 3) { error.textContent = "Write at least 3 beats — they become the narration."; $("bBeat1").focus(); return; }

    const scenario = scaffoldScenario(input);
    state.customScenarios.push(scenario);
    persist();
    dialog.close();

    state.category = "All";
    state.search = "";
    $("searchInput").value = "";
    renderCategoryChips();
    renderLibrary();
    selectScenario(scenario.id);
    announce(`“${scenario.title}” added to your library.`);
  });

  $("deleteScenarioBtn").addEventListener("click", () => {
    const scenario = getScenario(state.selectedId);
    if (!scenario || !scenario.custom) return;
    if (!window.confirm(`Delete your custom scenario “${scenario.title}”? Packages already saved to queue slots are kept.`)) return;
    state.customScenarios = state.customScenarios.filter(s => s.id !== scenario.id);
    state.selectedId = null;
    state.pkg = null;
    persist();
    $("packageSection").hidden = true;
    renderLibrary();
    renderWorkspace();
    announce("Custom scenario deleted.");
  });
}

/* ============================================================
   14c. STUDIO ASSISTANT HOST
   The chat UI and generic brains live in assistant.js (shared
   by every page). This section is the Studio-specific "host":
   the app context, the offline command parser, and the action
   whitelist - never anything destructive (no reset, no delete).
   ============================================================ */

function voiceLabel(id) {
  const v = VOICES.find(v => v.id === (id || state.options.voice));
  return v ? v.label : id;
}

/* Snapshot of what the user is looking at - sent with every AI request
   and used to answer "what's selected?" style questions offline. */
function assistantContext() {
  const scenario = getScenario(state.selectedId);
  return {
    selectedScenario: scenario ? {
      title: scenario.title,
      category: scenario.category,
      custom: Boolean(scenario.custom),
      beats: scenario.beats.length
    } : null,
    packageGenerated: Boolean(state.pkg),
    runtime: state.options.runtime,
    voice: voiceLabel(),
    searchQuery: state.search,
    categoryFilter: state.category,
    libraryTotal: allScenarios().length,
    customScenarios: state.customScenarios.length,
    lastSeed: state.seed ? `${state.seed.category}: ${state.seed.text}` : null,
    storageMode: storage.mode,
    categories: CATEGORIES,
    runtimes: RUNTIMES.map(r => r.id),
    voices: VOICES.map(v => v.label)
  };
}

/* "scary stories" -> "Scary Story": match a spoken category name,
   plural-tolerant, ignoring filler words like "videos" or "category". */
function resolveCategoryName(text) {
  const norm = s => s.toLowerCase().replace(/[""''\/]/g, " ")
    .replace(/\b(videos?|scenarios?|shorts?|ones?|category)\b/g, " ")
    .replace(/ies\b/g, "y").replace(/([a-z])s\b/g, "$1")
    .replace(/\s+/g, " ").trim();
  const rem = norm(text);
  if (!rem) return null;
  return CATEGORIES.slice().sort((a, b) => b.length - a.length)
    .find(c => { const cl = norm(c); return cl === rem || rem.includes(cl); }) || null;
}

/* Loose title match: "open the moon one" should find the Moon scenario. */
function findScenarioByTitle(text) {
  const stop = new Set(["the", "a", "an", "one", "that", "scenario", "video", "what", "if", "about"]);
  const words = String(text).toLowerCase().replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/).filter(w => w && !stop.has(w));
  if (!words.length) return null;
  let best = null, bestScore = 0;
  allScenarios().forEach(s => {
    const hay = (s.title + " " + s.tags.join(" ")).toLowerCase();
    const score = words.reduce((n, w) => n + (hay.includes(w) ? 1 : 0), 0);
    if (score > bestScore) { best = s; bestScore = score; }
  });
  return bestScore >= Math.max(1, Math.ceil(words.length / 2)) ? best : null;
}

/* Story categories keep the topic as a plain narrative title; what-if
   categories phrase it as the signature question. (CATEGORY_CTA's keys
   are exactly the story categories.) */
function assistantTitleFor(raw, category) {
  const clean = raw.replace(/[.?!]+$/, "");
  if (CATEGORY_CTA[category]) return clean.charAt(0).toUpperCase() + clean.slice(1);
  return /^what\s+if\b/i.test(raw) ? raw : `What if ${clean}?`;
}

/* Create a custom scenario without opening the dialog. Uses the same AI
   draft service as "Write it for me"; falls back to the prefilled builder
   when the dashboard is offline. */
async function assistantCreateScenario(args) {
  let raw = String(args.title || "").trim().replace(/\s+/g, " ");
  if (!raw) return "Give me a topic — e.g. “make a video about haunted vending machines”.";
  const category = CATEGORIES.includes(args.category) ? args.category : "Speculative";
  const title = assistantTitleFor(raw, category);
  let draft;
  try {
    draft = await draftScenarioWithAI(title, category, state.options.runtime);
  } catch (err) {
    $("newScenarioBtn").click();
    $("bTitle").value = title;
    return err && err.message === "dashboard-offline"
      ? "The AI writer needs the Studio helper running — I opened the builder with your title instead. Fill in the beats yourself, or start “Start-What-If-Studio” and click “Write it for me”."
      : "The writing service hiccuped — I opened the builder with your title. Try “Write it for me” again in a moment.";
  }
  const scenario = scaffoldScenario({
    title,
    category,
    glyph: draft.emoji,
    premise: draft.premise,
    tags: draft.tags,
    beats: draft.beats
  });
  state.customScenarios.push(scenario);
  persist();
  state.category = "All";
  state.search = "";
  $("searchInput").value = "";
  renderCategoryChips();
  renderLibrary();
  selectScenario(scenario.id);
  if (args.render) {
    $("generateBtn").click();
    return `Created “${scenario.title}” (draft by ${draft.engine}) and exported it for render — the watcher takes it from here. Everything is editable if you want another cut.`;
  }
  return `Added “${scenario.title}” to your library (draft by ${draft.engine}) and opened it. Review the beats, then say “generate” to send it to render.`;
}

/* Whitelisted actions - the only things chat (local or AI) can do.
   Each returns a human status line. */
async function runAssistantAction(action) {
  const args = (action && action.args) || {};
  switch (action && action.name) {
    case "select_scenario": {
      const s = findScenarioByTitle(String(args.title || ""));
      if (!s) return `I couldn't find a scenario matching “${String(args.title || "").slice(0, 60)}” — try “search ${String(args.title || "").split(/\s+/)[0] || "…"}” to browse.`;
      selectScenario(s.id);
      return `Opened “${s.title}” (${s.category}). Say “generate” to build and export it.`;
    }
    case "search": {
      if (args.category && CATEGORIES.includes(args.category)) state.category = args.category;
      else if (args.category === "All") state.category = "All";
      state.search = String(args.query || "").slice(0, 80);
      $("searchInput").value = state.search;
      renderCategoryChips();
      renderLibrary();
      const n = filteredScenarios().length;
      return n
        ? `Showing ${n} scenario${n === 1 ? "" : "s"}${state.search ? ` for “${state.search}”` : ""}${state.category !== "All" ? ` in ${state.category}` : ""}. Tell me which to open.`
        : "No matches — try different words, or say “make a video about …” and I'll draft a new one.";
    }
    case "set_options": {
      const parts = [];
      const rt = Number(args.runtime);
      if (RUNTIMES.some(r => r.id === rt)) {
        state.options.runtime = rt;
        if (getScenario(state.selectedId)) renderRuntimeControl();
        syncBuilderRuntime();
        parts.push(`runtime ${rt === 180 ? "3 min" : rt + "s"}`);
      }
      const vid = String(args.voice || "").toLowerCase();
      const voice = VOICES.find(v => v.id === vid || v.label.toLowerCase().includes(vid));
      if (voice && vid) {
        state.options.voice = voice.id;
        const sel = $("voiceSelect");
        if (sel.options.length) sel.value = voice.id;
        parts.push(`voice ${voice.label}`);
      }
      return parts.length
        ? `Done — ${parts.join(", ")}. This applies to the next package you generate.`
        : "I can set runtime to 30s, 60s, 90s or 3 min, and the voice to Calm, High-Energy or Deadpan.";
    }
    case "generate": {
      const scenario = getScenario(state.selectedId);
      if (!scenario) return "Pick a scenario first — say “open …” with a title, or “make a video about …” for a new one.";
      $("generateBtn").click();
      return `Generated “${scenario.title}” (${state.options.runtime === 180 ? "3 min" : state.options.runtime + "s"}, ${voiceLabel()}) and downloaded the render queue — the watcher picks it up from Downloads.`;
    }
    case "export": {
      if (!state.pkg) {
        const scenario = getScenario(state.selectedId);
        if (!scenario) return "Nothing to export yet — open a scenario and say “generate” first.";
        state.pkg = buildPackage(scenario, state.options);
        state.activeTab = 0;
        renderPackage();
      }
      const format = String(args.format || "json").toLowerCase();
      if (format === "txt") { $("exportTxtBtn").click(); return "Exported the package as .txt."; }
      if (format === "srt") { $("exportSrtBtn").click(); return "Exported the subtitles as .srt."; }
      $("exportJsonBtn").click();
      return "Exported the render .json — the watcher will pick it up from Downloads.";
    }
    case "new_seed": {
      nextSeed();
      return `Here's a fresh angle — ${state.seed.category}: ${state.seed.text} Say “make a video about it” and I'll draft it.`;
    }
    case "create_scenario":
      return assistantCreateScenario(args);
    case "render_category": {
      const cat = CATEGORIES.includes(args.category) ? args.category
        : resolveCategoryName(String(args.category || ""));
      if (!cat) return "Tell me which category — e.g. “render all scary stories” or “render all true history”.";
      const n = exportCategoryForRender(cat);
      if (!n) return `There are no scenarios in ${cat} yet.`;
      return `Exported all ${n} ${cat} scenario${n === 1 ? "" : "s"} as one render queue (${state.options.runtime === 180 ? "3 min" : state.options.runtime + "s"}, ${voiceLabel()}) — the watcher renders them back-to-back, a few minutes each.`;
    }
    case "navigate": {
      const page = String(args.page || "").toLowerCase();
      if (page.startsWith("video")) { $("navVideosBtn").click(); return "Checking the dashboard and heading to Videos…"; }
      if (page.startsWith("produce")) { $("navProduceBtn").click(); return "Checking the dashboard and heading to Produce…"; }
      if (page.startsWith("spend")) { $("navSpendBtn").click(); return "Checking the dashboard and heading to Spend…"; }
      if (page.startsWith("help") || page.startsWith("how")) { $("navHelpBtn").click(); return "Opening the how-to guide…"; }
      if (page.startsWith("studio")) return "You're already in the Studio.";
      return "I can take you to Videos, Produce, Spend, or the How-to guide.";
    }
    default:
      return null;
  }
}

const ASSISTANT_CAPABILITIES =
  "I can drive the studio for you — try:\n" +
  "• “open the black hole scenario”\n" +
  "• “make a 90s deadpan video about haunted elevators”\n" +
  "• “set the voice to high-energy” / “make it 3 min”\n" +
  "• “generate” (build + export the selected scenario)\n" +
  "• “search history” or “show scary ones”\n" +
  "• “render all scary stories” (one queue, the watcher renders the whole category)\n" +
  "• “give me an idea”, “go to produce”, “export srt”\n" +
  "• “is my video done?” (render status + newest videos)\n" +
  "• “give me the caption for my newest video” (post kit, ready to copy)\n" +
  "• “mark it posted” once a video has gone out\n" +
  "…and ask me anything about how the app or the render pipeline works.";

/* Local intent parsing - fast, free, and works offline. Returns
   { action, reply } or null (which hands off to the AI tier). */
function parseIntent(raw) {
  const text = raw.trim();
  const t = text.toLowerCase().replace(/[""'']/g, "");
  if (!t) return null;

  if (/what('?s| is) (selected|open|loaded)|current (settings|status|setup)|^status$/.test(t)) {
    const c = assistantContext();
    return { reply: (c.selectedScenario
      ? `You have “${c.selectedScenario.title}” open (${c.selectedScenario.category}${c.selectedScenario.custom ? ", custom" : ""}).`
      : "Nothing is selected yet.")
      + ` Settings: ${c.runtime === 180 ? "3 min" : c.runtime + "s"}, ${c.voice}. Library: ${c.libraryTotal} scenarios (${c.customScenarios} custom).`
      + (c.packageGenerated ? " A package is generated and ready to export." : "") };
  }

  const nav = t.match(/^(?:go to|take me to|open|show me|show)\s+(?:the\s+)?(videos?|produce|spend|help|how[- ]to|dashboard|guide)\b/);
  if (nav) {
    const page = /help|how|guide/.test(nav[1]) ? "help" : (nav[1] === "dashboard" ? "videos" : nav[1]);
    return { action: { name: "navigate", args: { page } } };
  }

  if (/^(?:give me |get me |i need )?(?:a |another |new |fresh )?(?:seed|idea|angle|inspiration)\b/.test(t) ||
      /new scenario seed/.test(t))
    return { action: { name: "new_seed", args: {} } };

  // Settings: runtime and/or voice in one message ("make it a 90s hype video").
  const rtMatch = t.match(/\b(30|60|90|180)\s*s?(?:ec(?:ond)?s?)?\b/) || (/\b3\s*min/.test(t) ? ["", "180"] : null);
  const voiceMatch = t.match(/\b(calm|hype|high[\s-]?energy|deadpan)\b/);
  const settingsIntent = /\b(set|change|switch|use|make it|runtime|length|voice|style)\b/.test(t);
  if (settingsIntent && (rtMatch || voiceMatch) && !/\babout\b/.test(t)) {
    const args = {};
    if (rtMatch) args.runtime = Number(rtMatch[1]);
    if (voiceMatch) args.voice = voiceMatch[1].startsWith("high") ? "hype" : voiceMatch[1];
    return { action: { name: "set_options", args } };
  }

  if (/^(generate|render|export for render|make (?:the|this) video|build (?:the |this )?package|send it|do it|go|ship it)\W*$/.test(t))
    return { action: { name: "generate", args: {} } };

  const exp = t.match(/^export\b.*?\b(txt|srt|json|text|subtitles?)\b|^(?:download|save)\b.*\b(txt|srt|json)\b/);
  if (exp) {
    const f = (exp[1] || exp[2] || "json").replace("text", "txt").replace(/subtitles?/, "srt");
    return { action: { name: "export", args: { format: f } } };
  }
  if (/^export\W*$/.test(t)) return { action: { name: "export", args: { format: "json" } } };

  // Batch: "render all scary stories" -> one multi-slot queue for the watcher.
  const batch = t.match(/^(?:render|generate|export|make|build|queue)\s+(?:all|every|the whole|the entire)\s+(.+)$/);
  if (batch) {
    const rem = batch[1];
    const cat = /^(?:of\s+)?(?:them|these|those|it|this|the)?\s*category\W*$|^(?:of\s+)?(?:them|these|those)\W*$/.test(rem)
      ? (state.category !== "All" ? state.category : null)
      : resolveCategoryName(rem);
    if (cat) return { action: { name: "render_category", args: { category: cat } } };
  }

  // Creation: "make a video about X", "make a scary story about X",
  // or a bare "what if ...?" premise.
  const create = t.match(/^(?:make|create|write|draft|build)(?:\s+me)?(?:\s+(?:a|an|another|new))?\s*(?:\d+\s*s?|3\s*min)?\s*(?:calm|hype|high[\s-]?energy|deadpan)?\s*(?:scary|creepy|horror|spooky|true history|history|historical)?\s*(?:scenario|video|short|story|one)?\s*(?:about|on|called|for|:)\s*(.+)$/);
  if (create || /^what\s+if\s+.+/.test(t)) {
    const topic = create ? create[1] : text;
    const render = /\b(and )?(render|export|ship|send) it\b|right now/.test(t);
    // "…and render it" is an instruction, not part of the title.
    const title = topic.replace(/[\s,]*\b(?:and\s+)?(?:render|export|ship|send)\s+it\W*$|[\s,]*\bright now\W*$/, "").trim();
    const args = { title, render };
    if (rtMatch || voiceMatch) {
      // Apply inline settings before drafting.
      const opts = {};
      if (rtMatch) opts.runtime = Number(rtMatch[1]);
      if (voiceMatch) opts.voice = voiceMatch[1].startsWith("high") ? "hype" : voiceMatch[1];
      runAssistantAction({ name: "set_options", args: opts });
    }
    // Longest name first so "true history" isn't shadowed by "History".
    let cat = CATEGORIES.slice().sort((a, b) => b.length - a.length)
      .find(c => t.includes(c.toLowerCase()));
    if (!cat && /\b(scary|creepy|horror|spooky)\b/.test(t)) cat = "Scary Story";
    // A plain "history video about rome" wants the documentary category;
    // "history" stays the what-if flavor only for what-if questions.
    if (cat === "History" && !/^what\s+if\b/.test(args.title)) cat = "True History";
    if (cat) args.category = cat;
    return { action: { name: "create_scenario", args } };
  }

  const search = t.match(/^(?:search|find|filter|show)\s+(?:for\s+|me\s+)?(.+)$/);
  if (search) {
    const q = search[1].replace(/\s*(scenarios?|ones?|videos?)$/, "").trim();
    const cat = CATEGORIES.find(c => q.toLowerCase() === c.toLowerCase() ||
      (q.length > 3 && c.toLowerCase().startsWith(q.toLowerCase())));
    if (/^(all|everything)$/.test(q)) return { action: { name: "search", args: { query: "", category: "All" } } };
    return { action: { name: "search", args: cat ? { query: "", category: cat } : { query: q } } };
  }

  const open = t.match(/^(?:open|select|load|pick|choose)\s+(.+)$/);
  if (open) {
    if (findScenarioByTitle(open[1])) return { action: { name: "select_scenario", args: { title: open[1] } } };
    return { action: { name: "search", args: { query: open[1].replace(/^the\s+/, "") } } };
  }

  // A message that closely matches a library title ("the moon one").
  if (t.split(/\s+/).length <= 6) {
    const s = findScenarioByTitle(t);
    if (s) return { action: { name: "select_scenario", args: { title: t } } };
  }

  return null;
}

/* Register this page as the assistant's host. assistant.js (loaded after
   this file) builds the chat UI, handles smalltalk/FAQ/AI tiers, and calls
   back into these for everything Studio-specific. */
window.assistantHost = {
  page: "studio",
  capabilities: ASSISTANT_CAPABILITIES,
  getContext: assistantContext,
  parseIntent,
  runAction: runAssistantAction
};

/* ============================================================
   15. WIRING
   ============================================================ */

function bindWorkspaceActions() {
  $("generateBtn").addEventListener("click", () => {
    const scenario = getScenario(state.selectedId);
    if (!scenario) return;
    state.pkg = buildPackage(scenario, state.options);
    state.activeTab = 0;
    renderPackage();
    exportForRender(state.pkg);
    announce("Package generated and exported — the watcher renders it from Downloads. Edit anything and hit Export .json to send a new cut.");
    const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    $("packageSection").scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "nearest" });
  });

  $("voiceSelect").addEventListener("change", (event) => {
    state.options.voice = event.target.value;
  });

  $("copySectionBtn").addEventListener("click", () => {
    if (!state.pkg) return;
    const tab = TAB_DEFS[state.activeTab];
    copyText(tabContent(state.pkg, tab.id).text, tab.label);
  });

  $("copyAllBtn").addEventListener("click", () => {
    if (!state.pkg) return;
    copyText(packageToText(state.pkg), "Full package");
  });

  $("exportTxtBtn").addEventListener("click", () => {
    if (!state.pkg) return;
    downloadFile(slugify(state.pkg.title) + ".txt", packageToText(state.pkg));
    announce("Package exported as .txt.");
  });

  $("exportSrtBtn").addEventListener("click", () => {
    if (!state.pkg) return;
    downloadFile(slugify(state.pkg.title) + ".srt", packageToSrt(state.pkg));
    announce("Subtitles exported as .srt.");
  });

  $("exportJsonBtn").addEventListener("click", () => {
    if (!state.pkg) return;
    exportForRender(state.pkg);
    announce("Package exported for render.");
  });
}

function bindGlobalActions() {
  $("searchInput").addEventListener("input", (event) => {
    state.search = event.target.value;
    renderLibrary();
  });

  $("newSeedBtn").addEventListener("click", nextSeed);

  $("copySeedBtn").addEventListener("click", () => {
    if (!state.seed) return;
    copyText(`${state.seed.category}: ${state.seed.text}`, "Seed");
  });

  $("resetAllBtn").addEventListener("click", resetAll);

  $("navToggle").addEventListener("click", () => {
    setNavCollapsed(!document.body.classList.contains("nav-collapsed"));
  });

  const goToDashboard = async (path) => {
    const DASHBOARD = "http://127.0.0.1:8765/";
    const status = $("navStatus");
    status.textContent = "Checking…";
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 2500);
      await fetch(DASHBOARD + "api/videos", { signal: controller.signal });
      clearTimeout(timer);
      window.location.href = DASHBOARD + path;   // same tab - the sidebar's "Studio" goes back
    } catch (err) {
      setNavCollapsed(false, false);             // make sure the hint is visible
      status.textContent = "Dashboard offline — double-click “Start-What-If-Studio” in the project folder, then try again.";
      setTimeout(() => { status.textContent = ""; }, 8000);
    }
  };
  $("navVideosBtn").addEventListener("click", () => goToDashboard(""));
  $("navProduceBtn").addEventListener("click", () => goToDashboard("produce"));
  $("navSpendBtn").addEventListener("click", () => goToDashboard("spend"));
  $("navHelpBtn").addEventListener("click", () => { window.location.href = "help.html"; });

  bindArrowNav($("categoryChips"), ".chip", (item) => item.click());
  bindArrowNav($("runtimeGroup"), ".segment", (item) => item.click());
  bindArrowNav($("packageTabs"), ".tab", (item) => item.click());
}

/* ============================================================
   16. INIT
   ============================================================ */

function init() {
  let savedNav = null;
  try { savedNav = window.localStorage.getItem("wis.navCollapsed"); } catch (err) { /* ignore */ }
  setNavCollapsed(savedNav === null
    ? window.matchMedia("(max-width: 700px)").matches   // start collapsed on phones
    : savedNav === "1", false);
  restore();
  renderStorageBadge();
  renderCategoryChips();
  renderLibrary();
  renderWorkspace();
  bindWorkspaceActions();
  bindGlobalActions();
  bindBuilder();
}

document.addEventListener("DOMContentLoaded", init);
