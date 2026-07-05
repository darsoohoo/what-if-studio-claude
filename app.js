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
  "Scary/Weird"
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
  "Scary/Weird": ["#151a30", "#b83a6e"]
};

const PLATFORMS = [
  { id: "tiktok", label: "TikTok", aspect: "9:16 vertical", hashtags: "#whatif #storytime #interesting #fyp", cta: "Follow for tomorrow's what-if." },
  { id: "shorts", label: "YT Shorts", aspect: "9:16 vertical", hashtags: "#whatif #shorts #storytime", cta: "Subscribe — a new what-if drops next." },
  { id: "reels", label: "Reels", aspect: "9:16 vertical", hashtags: "#whatif #reels #didyouknow", cta: "Follow for the next scenario." }
];

const RUNTIMES = [
  { id: 30, label: "30s", beats: 3, note: "Tight cut: hook, three fast beats, out. Every word earns its place." },
  { id: 60, label: "60s", beats: 5, note: "Standard cut: full beat structure at a brisk pace." },
  { id: 180, label: "3 min", beats: 5, note: "Extended cut: expand each beat with one extra example, visual, or aside (~25–30s per beat)." }
];

const VOICES = [
  { id: "calm", label: "Calm Narrator", direction: "Low, steady, confident. Let pauses do the scaring. Never rush the payoff line." },
  { id: "hype", label: "High-Energy Storyteller", direction: "Fast, punchy, incredulous. Hit every twist like breaking news. Big emphasis on numbers." },
  { id: "deadpan", label: "Deadpan Documentarian", direction: "Flat, dry, matter-of-fact. Deliver the wildest lines like a weather report. Comedy lives in the contrast." }
];

const QUEUE_SIZE = 7;

const SLOT_STATUSES = ["Planned", "Scripted", "Recorded", "Edited", "Posted"];

const STORAGE_KEY = "whatIfStudio.v1";

/* ============================================================
   2. SCENARIO BANK — 24 scenarios, 3 per category
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
  options: { platform: "tiktok", runtime: 60, voice: "calm" },
  pkg: null,
  activeTab: 0,
  seed: null,
  seedRotation: { catIndex: 0, perCat: {} },
  customScenarios: [],
  queue: Array.from({ length: QUEUE_SIZE }, () => ({ pkg: null, status: SLOT_STATUSES[0], notes: "" }))
};

function persist() {
  storage.write({
    queue: state.queue,
    seedRotation: state.seedRotation,
    customScenarios: state.customScenarios
  });
}

function restore() {
  const saved = storage.read();
  if (!saved) return;
  if (Array.isArray(saved.queue) && saved.queue.length === QUEUE_SIZE) {
    state.queue = saved.queue.map(slot => ({
      pkg: slot && slot.pkg ? slot.pkg : null,
      status: slot && SLOT_STATUSES.includes(slot.status) ? slot.status : SLOT_STATUSES[0],
      notes: slot && typeof slot.notes === "string" ? slot.notes : ""
    }));
  }
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

function renderLibrary() {
  const grid = $("scenarioGrid");
  grid.innerHTML = "";
  const matches = filteredScenarios();
  $("libraryCount").textContent = `${matches.length} of ${allScenarios().length} scenarios`;
  $("libraryEmpty").hidden = matches.length > 0;

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

  renderSegmented($("platformGroup"), PLATFORMS.map(p => ({ value: p.id, label: p.label })), state.options.platform, v => { state.options.platform = v; });
  renderSegmented($("runtimeGroup"), RUNTIMES.map(r => ({ value: String(r.id), label: r.label })), String(state.options.runtime), v => { state.options.runtime = Number(v); });

  const voiceSelect = $("voiceSelect");
  voiceSelect.innerHTML = "";
  VOICES.forEach(v => voiceSelect.appendChild(el("option", { value: v.id, text: v.label })));
  voiceSelect.value = state.options.voice;
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
  const platform = PLATFORMS.find(p => p.id === options.platform) || PLATFORMS[0];
  const runtime = RUNTIMES.find(r => r.id === options.runtime) || RUNTIMES[1];
  const voice = VOICES.find(v => v.id === options.voice) || VOICES[0];

  const beats = scenario.beats.slice(0, runtime.beats);
  const outro = voice.id === "hype"
    ? `That's the timeline — tell me where it breaks. ${platform.cta}`
    : voice.id === "deadpan"
      ? `Anyway. ${platform.cta}`
      : `Sit with that one for a second. ${platform.cta}`;

  const captions = scenario.captions.map(c => `${c}\n${platform.hashtags}`);

  return {
    scenarioId: scenario.id,
    title: scenario.title,
    category: scenario.category,
    colors: { from: scenario.image.from, to: scenario.image.to },
    platform: platform.label,
    aspect: platform.aspect,
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
  lines.push("WHAT IF STUDIO — CONTENT PACKAGE");
  lines.push("=".repeat(40));
  lines.push(`Title:     ${pkg.title}`);
  lines.push(`Category:  ${pkg.category}`);
  lines.push(`Platform:  ${pkg.platform} (${pkg.aspect})`);
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
  lines.push("Made with What If Studio (local, offline). Content is speculative fiction / thought experiment.");
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
        html: `<h5>Shot list — ${escapeHtml(pkg.aspect)}, ${escapeHtml(pkg.platform)}</h5><ol>${pkg.shotList.map(s => `<li>${escapeHtml(s)}</li>`).join("")}</ol>`,
        text: pkg.shotList.map((s, i) => `${i + 1}. ${s}`).join("\n")
      };
    case "captions":
      return {
        html: `<h5>Caption options — ${escapeHtml(pkg.platform)}</h5><ol>${pkg.captions.map(c => `<li>${escapeHtml(c).replace(/\n/g, "<br>")}</li>`).join("")}</ol>`,
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
  $("packageMeta").textContent = `${pkg.platform} · ${pkg.runtimeLabel} · ${pkg.voice}`;

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

  const slotSelect = $("slotSelect");
  slotSelect.innerHTML = "";
  state.queue.forEach((slot, i) => {
    const label = slot.pkg ? `Slot ${i + 1} — ${slot.pkg.title}` : `Slot ${i + 1} — empty`;
    slotSelect.appendChild(el("option", { value: String(i), text: label }));
  });
}

/* ============================================================
   11. QUEUE
   ============================================================ */

function renderQueue() {
  const list = $("queueList");
  list.innerHTML = "";

  state.queue.forEach((slot, i) => {
    const card = el("div", { class: "queue-slot" + (slot.pkg ? " filled" : "") });
    const head = el("div", { class: "slot-head" }, [
      el("span", { class: "slot-name", text: `SLOT ${i + 1}` })
    ]);

    if (slot.pkg) {
      head.appendChild(el("button", {
        type: "button",
        class: "btn btn-ghost btn-small btn-danger-text",
        text: "Clear",
        "aria-label": `Clear slot ${i + 1}`,
        onclick: () => {
          if (!window.confirm(`Clear slot ${i + 1} (“${slot.pkg.title}”)? This removes the saved package and notes.`)) return;
          state.queue[i] = { pkg: null, status: SLOT_STATUSES[0], notes: "" };
          persist();
          renderQueue();
          renderPackage();
          announce(`Slot ${i + 1} cleared.`);
        }
      }));
    }
    card.appendChild(head);

    if (slot.pkg) {
      card.appendChild(el("p", { class: "slot-title", text: slot.pkg.title }));
      card.appendChild(el("p", { class: "slot-meta", text: `${slot.pkg.platform} · ${slot.pkg.runtimeLabel} · ${slot.pkg.voice}` }));

      const statusId = `slotStatus${i}`;
      const statusRow = el("div", { class: "slot-status-row" });
      statusRow.appendChild(el("label", { class: "field-label", for: statusId, text: "Status" }));
      const statusSelect = el("select", { id: statusId });
      SLOT_STATUSES.forEach(s => statusSelect.appendChild(el("option", { value: s, text: s })));
      statusSelect.value = slot.status;
      statusSelect.addEventListener("change", () => {
        state.queue[i].status = statusSelect.value;
        persist();
      });
      statusRow.appendChild(statusSelect);
      card.appendChild(statusRow);

      const exportBtn = el("button", {
        type: "button",
        class: "btn btn-ghost btn-small",
        text: "Export package",
        "aria-label": `Export package in slot ${i + 1}`,
        onclick: () => {
          downloadFile(slugify(slot.pkg.title) + ".txt", packageToText(slot.pkg));
          announce(`Slot ${i + 1} package exported.`);
        }
      });
      card.appendChild(exportBtn);
    } else {
      card.appendChild(el("p", { class: "slot-empty-text", text: "Empty — generate a package and save it here." }));
    }

    const notesId = `slotNotes${i}`;
    const notesLabel = el("label", { class: "field-label", for: notesId, text: "Tracker notes" });
    notesLabel.style.marginTop = "8px";
    const notes = el("textarea", { id: notesId, placeholder: "Recording notes, edits, posting plan…" });
    notes.value = slot.notes;
    notes.addEventListener("input", () => {
      state.queue[i].notes = notes.value;
      persist();
    });
    card.appendChild(notesLabel);
    card.appendChild(notes);

    list.appendChild(card);
  });
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
  const ok = window.confirm("Reset ALL local data? This clears every queue slot, all tracker notes, seed rotation, and your custom scenarios. Exported files are not affected.");
  if (!ok) return;
  storage.clear();
  state.queue = Array.from({ length: QUEUE_SIZE }, () => ({ pkg: null, status: SLOT_STATUSES[0], notes: "" }));
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
  renderQueue();
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
      "Hook shot: " + firstSentence(premise),
      ...input.beats.map(b => "Visual: " + firstSentence(b))
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

function bindBuilder() {
  const dialog = $("builderDialog");
  const form = $("builderForm");
  const error = $("builderError");

  const categorySelect = $("bCategory");
  CATEGORIES.forEach(c => categorySelect.appendChild(el("option", { value: c, text: c })));

  $("newScenarioBtn").addEventListener("click", () => {
    form.reset();
    error.textContent = "";
    dialog.showModal();
    $("bTitle").focus();
  });

  $("builderCancel").addEventListener("click", () => dialog.close());

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
   15. WIRING
   ============================================================ */

function bindWorkspaceActions() {
  $("generateBtn").addEventListener("click", () => {
    const scenario = getScenario(state.selectedId);
    if (!scenario) return;
    state.pkg = buildPackage(scenario, state.options);
    state.activeTab = 0;
    renderPackage();
    announce("Package generated.");
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
    // "whatifstudio-" prefix lets the pipeline watcher recognize the file.
    downloadFile("whatifstudio-package-" + slugify(state.pkg.title) + ".json", JSON.stringify(state.pkg, null, 2));
    announce("Package exported as .json.");
  });

  $("saveSlotBtn").addEventListener("click", () => {
    if (!state.pkg) return;
    const index = Number($("slotSelect").value);
    const slot = state.queue[index];
    if (slot.pkg) {
      const ok = window.confirm(`Slot ${index + 1} already holds “${slot.pkg.title}”. Overwrite it?`);
      if (!ok) return;
    }
    state.queue[index] = { pkg: state.pkg, status: SLOT_STATUSES[0], notes: slot.notes || "" };
    persist();
    renderQueue();
    renderPackage();
    announce(`Saved to slot ${index + 1}.`);
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

  $("exportQueueBtn").addEventListener("click", () => {
    const items = state.queue
      .map((slot, i) => slot.pkg ? { slot: i + 1, status: slot.status, notes: slot.notes, package: slot.pkg } : null)
      .filter(Boolean);
    if (!items.length) {
      announce("Queue is empty — save a package to a slot first.");
      return;
    }
    const payload = { app: "what-if-studio", format: 1, exportedAt: new Date().toISOString(), items };
    downloadFile("whatifstudio-queue.json", JSON.stringify(payload, null, 2));
    announce(`Queue exported — ${items.length} package${items.length === 1 ? "" : "s"}.`);
  });

  bindArrowNav($("categoryChips"), ".chip", (item) => item.click());
  bindArrowNav($("platformGroup"), ".segment", (item) => item.click());
  bindArrowNav($("runtimeGroup"), ".segment", (item) => item.click());
  bindArrowNav($("packageTabs"), ".tab", (item) => item.click());
}

/* ============================================================
   16. INIT
   ============================================================ */

function init() {
  restore();
  renderStorageBadge();
  renderCategoryChips();
  renderLibrary();
  renderWorkspace();
  renderQueue();
  bindWorkspaceActions();
  bindGlobalActions();
  bindBuilder();
}

document.addEventListener("DOMContentLoaded", init);
