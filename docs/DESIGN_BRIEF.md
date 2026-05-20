# The Daily Abstract — design brief

A reference document for visual design work (Claude Design, future
designers, contributors). Describes brand, identity, surfaces, components,
target audience, tone, and explicit anti-patterns. The brand is editorial,
not corporate SaaS.

---

## What we are

**The Daily Abstract** is a daily newsletter of new arXiv papers, curated
by the subscriber's choice of categories and keywords. Each morning at 7am
the subscriber receives a short edition (≤15 papers). Reply with paper
numbers ("1, 3, 5") and the PDFs come back as attachments.

Open source, self-hosted, $0/mo to run forever on free-tier infra.

We are not a "tool". We are a publication that happens to be machine-built.
Each edition feels hand-cut even if there's no human editor — the curation
comes from the subscriber's own filter, not a content team.

## Target persona (default)

**Active academic researcher** (PhD student, postdoc, junior or senior
professor). They:
- Read arXiv daily but feel they're drowning
- Have 3-5 categories of interest that overlap and shift over time
- Are loyal to publications that respect their time
- Sniff out "AI-startup pitch deck" aesthetic and bounce
- Trust serif typography and editorial layouts (they read journals)
- Appreciate dark mode for late-night sessions

Secondary personas (not the hero, but welcome): PhD applicants, ML
practitioners in industry, science journalists.

## Voice & tone

- **Confident but understated.** No exclamation marks. No "🚀". No
  "Revolutionize your...".
- **Editorial, not promotional.** "Today's edition" not "Get exclusive
  content".
- **Concrete, not aspirational.** "Reply with 1 3 5 to get the PDFs" not
  "Stay connected with the research community".
- **Respectful of intelligence.** Don't explain what arXiv is. Don't
  define "paper". Assume domain literacy.
- **Bilingual hint:** UI in English, email content can be Spanish (the
  product translates titles + abstracts to Spanish via MyMemory). The
  English UI signals "we're targeting global researchers including Latam";
  the Spanish digest signals "we serve underserved Latam readers".

## Visual identity

### Palette — "Charcoal Ember" (dark editorial)

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#13161A` | Page background (deep charcoal) |
| `--surface` | `#1A1E23` | Cards, inputs, raised areas |
| `--surface-elevated` | `#20252B` | Hover states, focus surfaces |
| `--text` | `#EDE9E0` | Body text (warm white) |
| `--text-muted` | `#86898E` | Secondary text |
| `--text-faint` | `#5D6066` | Tertiary text, disabled |
| `--accent` | `#D99C5E` | Primary accent (amber) — links, CTAs, brand |
| `--accent-hover` | `#E6B07A` | Accent hover |
| `--accent-soft` | `#2A211A` | Diluted amber for backgrounds |
| `--border` | `#2D3137` | Hairlines, dividers |
| `--border-strong` | `#3A4047` | Input borders, stronger separators |
| `--danger` | `#C26356` | Errors, destructive |
| `--success` | `#87A96B` | Success states |

**Paper-tone** (used inside the email preview card embedded on the
dark page, AND in the actual email template):

| Token | Hex | Use |
|---|---|---|
| `--paper-bg` | `#F4F1EA` | Cream paper background |
| `--paper-surface` | `#FFFFFF` | Inner card surface |
| `--paper-text` | `#1A1A1A` | Body on paper |
| `--paper-muted` | `#6B6B6B` | Secondary on paper |
| `--paper-accent` | `#B97F3D` | Darker amber (better contrast on cream) |
| `--paper-border` | `#E2DCCD` | Hairline on cream |

### Typography

- **Serif (headings, masthead, prose):** Georgia, 'Times New Roman',
  'Iowan Old Style', serif. Standard newspaper serif. Available everywhere,
  no web font load.
- **Sans (body, UI, labels):** system stack (`-apple-system`,
  BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica Neue, Arial).
- **Mono (code, paper IDs, technical labels):** `ui-monospace`,
  SFMono-Regular, Menlo, Consolas.

### Type scale (responsive)

| Token | Range | Use |
|---|---|---|
| `--text-xs` | 0.78rem | Eyebrows, captions, pills |
| `--text-sm` | 0.875rem | Labels, hints |
| `--text-base` | 1rem | Body |
| `--text-lg` | `clamp(1.1rem, 1rem + 0.3vw, 1.25rem)` | Lead paragraphs |
| `--text-xl` | `clamp(1.4rem, 1.2rem + 0.7vw, 1.75rem)` | Section heads |
| `--text-2xl` | `clamp(1.8rem, 1.4rem + 1.5vw, 2.5rem)` | Page heads |
| `--text-display` | `clamp(2.5rem, 1.5rem + 4vw, 4.5rem)` | Hero / masthead display |

### Spacing scale

`--space-1` 0.25rem → `--space-6` 4rem, plus `--space-section`
`clamp(3rem, 2rem + 4vw, 5rem)` for inter-section gaps.

### Radii

- `--radius-sm` 3px (chips, micro-elements)
- `--radius-md` 6px (cards, inputs, buttons)

---

## Surfaces (pages we ship)

| Surface | Path | Function |
|---|---|---|
| **Landing** | `/` | Hero + today's preview + subscribe form + FAQ |
| **Preview** | `/preview` | Standalone view of last digest (for "see a sample") |
| **Confirm OK** | `/confirm?token=...` (success) | Post-subscribe welcome |
| **Confirm expired** | `/confirm?token=...` (failure) | Invalid/expired token |
| **Unsubscribed** | `/unsubscribe?token=...` | Post-unsubscribe |
| **Manage** | `/manage?token=...` | Edit categories/keywords/cap |
| **Privacy** | `/privacy` | Privacy policy (prose, serif) |
| **Terms** | `/terms` | Terms of use (prose, serif) |
| **Email digest** | (rendered, not URL) | The actual daily edition |
| **Email confirm** | (rendered) | Double opt-in email |

## Components (reusable)

- **Masthead:** "THE DAILY ABSTRACT" in caps Georgia, with hairline rule
  below and right-aligned `Daily edition · DD Mon YYYY` meta.
- **Section heading:** small uppercase eyebrow in amber + hairline rule.
- **Hero:** small uppercase eyebrow + display serif headline + lead
  paragraph + primary CTA + secondary link.
- **Preview card** (`.preview-card`): cream paper aesthetic embedded on
  dark — paper-bg + paper-text + paper-accent. Mimics the email exactly.
  Has masthead, eyebrow "Editor's Pick", numbered paper rows.
- **Form fields:** input/textarea with surface background, subtle border,
  amber focus ring. Label above with optional `.label-meta` muted note.
- **Quick presets** (`.preset`): pill chips, hover amber outline, active
  state filled amber + bg color text.
- **Category catalog** (`.cat-list`): scrollable accordion of arXiv groups
  with checkboxes per code. Has search input that filters across.
- **Buttons:** `.btn.primary` (amber filled) and `.btn.ghost` (outline).
- **Status banner** (`.status`): left-border colored notice (success
  green, error red, default amber).
- **Pills:** small mono badges, used for category codes shown post-confirm.
- **FAQ:** `<dl>` with serif `<dt>` and muted `<dd>`.
- **Prose** (`.prose`): serif body for privacy/terms.
- **Footer:** brand name + tagline + nav (privacy, terms, github).

## Information architecture

### Landing (`/`)

Sections, in order, are currently centered in one 720px column. **That's
the problem we want to fix** — sponsor a sidebar layout (Stratechery /
Pitchfork) where:

- **Left sidebar (~220-260px):** masthead "THE DAILY ABSTRACT", short
  tagline, vertical nav anchoring to: Today's edition / Subscribe / How it
  works / FAQ, plus secondary links (Privacy, Terms, GitHub).
- **Right content (fluid, max ~720px from sidebar):** hero, today's
  edition preview embedded, subscribe form, how-it-works numbered list,
  FAQ.

On mobile (<768px) the sidebar collapses to a top stack: masthead +
horizontal nav scroller + content below.

### Manage (`/manage?token=...`)

Similar shell, but content is the manage form pre-filled with current
subscription.

### Confirm / unsubscribed / expired

Same shell, content is short — title + 1-2 paragraphs + CTA back to
landing.

### Privacy / Terms

Same shell, prose content, narrower (~65ch) reading width inside the main
content area.

## Anti-patterns (what NOT to do)

- ❌ "Hero with gradient blob + centered headline" — generic AI startup
- ❌ Animated emoji or gradients shifting colors
- ❌ Big CTAs in saturated red/green/blue (use amber, the brand color)
- ❌ "AI-generated illustrations" of robots/brains/networks
- ❌ Glassmorphism / heavy blur / neumorphism — wrong era
- ❌ "Modal popups" or scroll-triggered interrupts
- ❌ Auto-playing video hero
- ❌ Newsletter signup interstitial covering the page on scroll
- ❌ "Trusted by 10,000+ companies" social proof rows (we have none, don't
  fake it)
- ❌ Dark UI that uses pure black `#000` — too harsh, use `#13161A`
- ❌ Sans-serif everywhere — kills the editorial feel
- ❌ Generic illustration libraries (Storyset, undraw) — anti-editorial
- ❌ Confetti / celebration animations on confirm — overdone

## References that DO match our intended feel

- **Stratechery** (stratechery.com) — sidebar editorial, serif headlines,
  premium publication feel
- **The Browser** (thebrowser.com) — single-column editorial newsletter
- **The Marginalian** (themarginalian.org) — long-form serif, careful
  hierarchy
- **Pitchfork** (pitchfork.com) — review aesthetic, masthead-heavy,
  asymmetric grids
- **NYT Cooking** (cooking.nytimes.com) — light surface variant of the
  same editorial logic

## Mockup data (use real strings, not Lorem)

If you generate preview/sample digest cards, use these realistic papers
(actual recent arXiv-style titles + abstracts trimmed):

```
01  Attention Is All You Need — Vaswani et al.
    The Transformer architecture relies entirely on attention mechanisms,
    dispensing with recurrence and convolutions. We show superior quality
    while being more parallelizable and requiring less time to train.

02  Federated Scheduling for Edge Kubernetes Clusters — Patel
    A control-plane design that coordinates pod placement across
    geographically distributed edge nodes with sub-100ms latency targets.

03  Sparse-Reward RL Without Manual Shaping — Wu
    We propose an intrinsic motivation signal that allows agents to learn
    from sparse rewards without engineered reward shaping, with SOTA on
    Atari.
```

## Functional constraints (don't break)

The generated HTML will be integrated into a Jinja2 template system. Any
generated mockup is fine — I (Claude Code) will:

1. Extract structural HTML and refactor into `{% extends "_base.html" %}`
2. Move CSS into the existing `app.css` with the design tokens already
   defined above
3. Preserve all form `name=` attributes (`email`, `categories[]`,
   `keywords`, `max_papers`) — backend depends on them
4. Preserve JS hooks (`#cat-search`, `#cat-list`, `#submit-btn`,
   `#presets`, `data-preset-id`, `data-search`) — `app.js` depends on them
5. Preserve route URLs (`/subscribe`, `/manage`, `/preview`, `/privacy`,
   `/terms`, `/unsubscribe`)

So: optimize for **layout, type scale, color use, hierarchy, spacing,
mood** — don't optimize for HTML/CSS purity. We'll refactor.

## Tagline alternatives for the hero

In rough order of preference:

1. "New arXiv papers, hand-cut to your interests."
2. "Your morning briefing of new research."
3. "A daily edition of new papers, in your inbox by 7am."
4. "Pick your categories. Read tomorrow's research today."

Pair with a sub-lead like:

> Choose the arXiv categories you follow. Each morning you get a short
> edition of new papers that match. Reply with the numbers to receive the
> PDFs.

## What's worth obsessing over

1. **Type rhythm.** Vertical rhythm between sections, hero leading, body
   leading. Make a researcher feel "this person thinks about typography".
2. **Hierarchy without size.** Eyebrows in small uppercase amber + strong
   serif headlines often more powerful than huge text.
3. **One color, used well.** Amber is the only chromatic note. Resist the
   urge to add a second accent.
4. **Hairlines.** Single-pixel borders are the editorial language. Use them
   liberally to structure space.
5. **The preview card.** The cream-on-dark moment. It's the only place the
   product visibly *is* the email. Make it the visual hero.

## What's worth NOT obsessing over

- Custom icons. Use unicode glyphs or simple SVG inlines for arrows.
- Logo. Wordmark only. No glyph, no symbol. The wordmark IS the brand.
- Imagery. We have none and shouldn't fake it with stock.
- Animations. A subtle hover state is enough. No scroll-triggered.
