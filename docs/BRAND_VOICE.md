# The Daily Abstract — brand voice profile

A reusable profile derived from the live product copy, design brief, templates, and commit history. Source of truth for any new copy decision. If a piece of writing doesn't pass this profile, rewrite it.

## 1. Essence

The Daily Abstract sounds like a thoughtful editor with a typography habit, not a SaaS landing page. We write as a *publication that happens to be software* — confident, understated, concrete, faintly literary. Every claim is backed by a real number, a real mechanism, or a real link; nothing is aspirational. The reader is an academic who already knows what arXiv is, has too much to read, and will bounce the moment we sound like a pitch deck.

## 2. Tone dimensions

- **Formal ↔ Casual:** *editorial-casual.* Contractions are fine ("you're in", "we don't even know who you are"), but no slang, no exclamation marks. Evidence: `"You're <em>in</em>."` (confirm_ok), `"You're <em>out</em>."` (unsubscribed).
- **Serious ↔ Playful:** *dry-witty.* Wit appears in italics and parentheticals, never in jokes. Evidence: terms.html — *"Use the service to bulk-scrape arXiv. (It already does that, once, for everyone.)"* and *"Disputes, if any, will be handled informally between humans."*
- **Technical ↔ Accessible:** *technical without explanation.* We name `Reply-To`, `List-Unsubscribe`, `cs.LG`, MyMemory, Mailsac without defining them. Evidence: DESIGN_BRIEF.md — *"Don't explain what arXiv is. Don't define 'paper'. Assume domain literacy."*
- **Promotional ↔ Editorial:** *editorial, almost anti-promotional.* "Today's edition" not "Get exclusive content". Evidence: form.html eyebrow *"A daily briefing for researchers"*, kicker *"In which the morning's research is cut to size."*
- **Aspirational ↔ Concrete:** *concrete to a fault.* Specifics ("~165 MB RAM idle", "1 GB shared-CPU VM", "thirty seconds", "every 10 minutes", "valid 48 h") replace adjectives. Evidence: form.html, README.md, privacy.html throughout.
- **Effusive ↔ Restrained:** *restrained.* No "Excited to share". No "🚀". Sole chromatic note is amber; the writing matches — one register, held.

## 3. Vocabulary

**We use:**

- *edition, masthead, colophon, folio, Vol. I, No. 03, deck, kicker, eyebrow* — newspaper diction
- *hand-cut, editor-curated, editor's cut, editor's pick* — artisan-editorial framing
- *short, briefing, morning, in your inbox by 7 a.m.* — temporal calm
- *self-hosted, free-tier, open source, MIT, indie, hobby project* — credibility through smallness
- *signed token, snapshot, listener, the union of every subscriber's filter* — mechanism words, used unapologetically
- *thirty seconds, ~30 s, ~165 MB, 48 h, 1 GB* — numbers with units

**We avoid:**

- *revolutionize, seamless, powerful, cutting-edge, AI-powered, supercharge, unlock, magic, effortless*
- *"Get exclusive content", "Stay connected", "Join 10,000+ researchers"* — fake social proof, generic CTAs
- exclamation marks, em-dash overdose substituting for thought, emoji decorations
- *"not X, just Y"*, *"no fluff"*, *"Excited to share"*, founder-journey filler

## 4. Rhythm and structure

- **Sentence length:** mixed but compressed; most fall in 8–18 words. We open with the short, declarative move (*"You're in."* / *"Short version: your email address, your category list, and nothing else."*) then qualify in a longer follow-up sentence.
- **Em-dashes:** load-bearing — they introduce a tightening or a sharper alternative, used roughly once per paragraph. Example: *"Choose the arXiv categories you follow. Each morning you get a short edition of new papers that match — titles and abstracts translated to Spanish, with the originals one link away."*
- **Parentheticals:** narrow, qualify, or under-mine. *"(It already does that, once, for everyone.)"* / *"(your local time)"*. Never used for cuteness.
- **Italics:** for emphasis on a single load-bearing word (*in*, *out*, *fine*, *you*, *editor-curated*), and for quoted commands (*STOP*, *DELETE*, *"quiero el 2 y el 7"*).
- **Lists:** short and parallel; bullets are sentences, not phrases. Privacy and Terms use bullet lists; landing copy stays in prose.
- **Bilingual register:** English UI + Spanish digest body, never code-switched in the same sentence in a system message. Inside the email, Spanish is plain and instructional: *"Responde a este correo con los números de los papers que quieres leer."*
- **Numbering:** we count things ("01 — Today's edition", "Vol. I · No. 03", "01 / 02 / 03") as a typographic gesture, not as a faux taxonomy.

## 5. Anti-voice (do not write)

From DESIGN_BRIEF.md anti-patterns plus inferred:

- *"🚀 Get the daily papers delivered to your inbox!"* — exclamation, emoji, promotional verb
- *"Revolutionize your research workflow with AI-powered curation"* — banned vocabulary stack
- *"Join 10,000+ researchers staying ahead of the curve"* — fake social proof, cliché
- *"We're excited to bring you a brand new way to read arXiv"* — founder-voice filler
- *"Stay connected with the research community"* — abstract, aspirational
- *"Sign up now — it's free!"* — exclamation, hard sell; we say *"Confirm by email →"*
- *"Hey researcher! Drowning in arXiv? We've got you. 🙌"* — wrong register top to bottom

## 6. Voice across surfaces

| Surface | Register | Move |
|---|---|---|
| Hero / landing | editorial, declarative, italics on the verb | *"New arXiv papers, hand-cut to your interests."* + concrete deck below |
| System messages (confirm, unsubscribe) | short, warm, italic on one word | *"You're in."* / *"You're out."* + one factual lead paragraph |
| Legal (privacy, terms) | plain editorial prose with a one-line summary up top, then bullets | *"Short version: your email address, your category list, and nothing else."* — bullets follow |
| Email digest body | Spanish, instructional, no marketing voice | *"Hoy 4 papers nuevos. Responde con los números para recibir los PDFs adjuntos."* |
| Email transactional (confirm) | minimal, two paragraphs, one CTA, one quiet fallback | *"You're one click away from receiving The Daily Abstract at <email>."* + *"If this wasn't you, ignore this email — the subscription won't activate without confirmation."* |
| Commit messages | conventional commits, Spanish, terse, lowercase scope | *"feat(digest): integrar translator con fallback a ingles"* |
| Documentation (README) | technical Spanish, present tense, command-first | *"Cada email lleva un footer + `List-Unsubscribe` personalizado."* |

The shift across surfaces is in *content*, not in *voice*: the same editor wrote all of it. Marketing copy is not louder than legal; legal is not stiffer than marketing.

## 7. Micro-prompts (generic → our voice)

1. *"Sign up for our newsletter!"* → **"Start subscription →"** (button) / **"Confirm by email →"** (commit step)
2. *"Thanks for subscribing! You're all set."* → **"You're *in*. Tomorrow at 7 a.m. (your local time) the first edition lands in your inbox."**
3. *"We respect your privacy."* → **"Short version: your email address, your category list, and nothing else. No trackers, no analytics, no cookies."**
4. *"Sorry to see you go!"* → **"You're *out*. Your address has been removed from the subscriber table. No more editions, no retention emails, no win-back campaigns."**
5. *"Get personalized AI-curated research delivered daily!"* → **"Pick the arXiv categories you follow. Each morning at 7 a.m. you get a short edition of new papers that match — reply with the numbers to get the PDFs."**
