# Frontend review — The Daily Abstract landing

Review of the redesigned web surfaces in `subscriptions/templates/` and `subscriptions/static/`. Scoped to a server-rendered FastAPI + Jinja2 + vanilla JS stack — patterns are evaluated against `docs/DESIGN_BRIEF.md` and `_design_handoff/design_handoff_web_surfaces/README.md`, not against SPA assumptions.

---

## TL;DR

- **One showstopper bug**: `subscriptions/static/app.js` declares `const form` twice (L201, L208) — this is a hard `SyntaxError` at parse time. The entire script never executes, so presets, search, chips, cap sync, edition switcher, GitHub stats, smooth-scroll nav, and submit guard are all dead in the browser right now. **Nothing else on this page is wired**. Fix before anything else.
- **Two broken navigation links** on `confirm_expired.html` and `unsubscribed.html`: `href="Landing Page.html"` (the design-handoff filename) instead of `/`. Users hitting either page after the happy/sad path will 404.
- **Dead CSS not stripped**: the entire `.tweaks-panel` design-time scaffolding (~180 lines, ~5 KB) is still in `app.css` (L1452–1627). The handoff README is explicit that it must be removed for production. No HTML references it; it's pure deadweight.
- **Massive layout-block duplication**: `.colophon` and `.full-footer` (~30 lines each) are copy-pasted into all 6 child templates. They belong in `_base.html` as `{% block colophon %}{% endblock %}` / `{% block footer %}{% endblock %}` slots, or unconditionally in the base.
- **Folio strip is duplicated 6×** the same way — it's identical except for one piece of right-side label text. Trivial extraction win.
- **`_digest_preview.html` has diverged from the new design system** — it uses `.preview-card-header`, `.preview-card-eyebrow`, `.preview-card-paper-number`, `.preview-fallback-note` etc., none of which exist in the new `app.css`. The `/preview` route renders an unstyled card. Either kill the route (the handoff README says it's "superseded by the editions switcher") or rewrite the partial against the `.pv-*` class system.
- **Visual identity is genuinely strong** — editorial direction is consistent, type rhythm is intentional, the cream-on-charcoal preview card is the visual hero the brief asks for, and the wordmark/sidebar/folio system reads as a publication, not as SaaS. The handoff was integrated faithfully where it was integrated.
- **27 inline `style="…"` attributes** across `confirm_ok.html`, `confirm_expired.html`, `unsubscribed.html` — large enough to be component candidates (welcome card, error explainer, error-eyebrow, pill list). Extract.
- **No CSP, no `og:image`, no `loading` attrs** — the brief and handoff README both call these out. Production-readiness gaps.
- **All Jinja form hooks preserved**: `name="email"`, `name="categories"`, `name="keywords"`, `name="max_papers"`, plus `#cat-search`, `#cat-list`, `#presets`, `#submit-btn`, `data-preset-id`, `data-search`. Backend POST will work. JS hooks would also work, *if the JS file loaded*.

---

## Strengths

What's working — reinforce, don't rebuild:

- **Visual point of view is committed.** Charcoal Ember palette + Georgia serif + amber as the single chromatic accent is consistent everywhere. There's zero gradient-blob / glassmorphism / "AI hero" energy. The brief's anti-pattern checklist (DESIGN_BRIEF.md L190–206) is respected end to end.
- **Type system is right.** Display headlines in serif (`.hero-title` L286–292 in `app.css`), italic kicker + deck for editorial flair (`.hero-kicker`, `.hero-deck-line`), monospace for paper IDs and tags. The eyebrow → display headline → italic deck → lead → CTA cadence is well-orchestrated in `form.html` L11–42.
- **Hairline editorial language.** `--rule: 1px solid var(--border)` is used liberally and disciplined — every section heading (L248), every nav item, every FAQ Q&A, the folio top/bottom. That's the publication feel the brief asked for ("hairlines are the editorial language").
- **The preview card is the visual hero.** `.preview-card` (L400–411) gets the deep shadow stack, the postmark SVG, and the `letter-card-on` -0.7° tilt — exactly what the brief flagged as "the cream-on-dark moment" worth obsessing over.
- **Real social proof is honest.** The GitHub IIFE (`app.js` L358–463) shows `· ★ N` only when stars exist, and grows footer stats progressively as forks/issues land. No fake "Trusted by N companies".
- **Asymmetric sidebar shell.** Stratechery-style layout (`.shell` L97–105) is intact, and the sticky sidebar (L111–122) with masthead → nav → secondary → colophon hierarchy reads as intentional publication chrome.
- **Mobile fallback is sensible.** At ≤880px the sidebar collapses to a horizontal scroller (L1202–1239), the preview card tilt is disabled (L1250), reply-flow stacks vertically (L1246–1248). The brief's responsive table (handoff §13) is implemented faithfully.
- **Accessibility scaffolding is in place.** `aria-labelledby` on every section, `aria-live="polite"` on `#selected-chips`, `aria-hidden="true"` on decorative elements, explicit `<label for>` associations on inputs, `:focus-visible` outlines on every interactive (L672–687).
- **Color contrast meets WCAG.** `--text` on `--bg` = ~14:1 AAA; `--text-muted` on `--bg` = ~5:1 AA.
- **Email digest matches web preview palette.** `digest/templates/digest.html` uses the exact same `#f4f1ea` / `#b97f3d` / `#1a1a1a` paper-tone tokens (inline as required by email-safe HTML). Voice continuity is real.

---

## Critical issues — fix before deploy

### C1 — `app.js` is dead at parse time (BLOCKING)

`subscriptions/static/app.js` L201 and L208 both declare `const form = document.getElementById('subscribe-form')`. This is a `SyntaxError: Identifier 'form' has already been declared`. The browser stops parsing the whole file, so:

- presets / chips / category search / cap sync — broken
- edition switcher — broken (preview card stays on the ML mock forever)
- sidebar IntersectionObserver active state — broken
- smooth scroll on hash links — broken
- GitHub stats fetch — broken (folio + sidebar never show `Issue NN`/`★ N`)
- empty-categories submit guard — broken

**Fix**: delete L201–203 (the original block) and keep the L208–218 client-side guard. Same line, single declaration.

```js
/* L198–219 should become: */
/* ============================
   FORM SUBMIT — client guard
============================ */
const form = document.getElementById('subscribe-form');
if (form) {
  form.addEventListener('submit', (e) => {
    const codes = getSelectedCodes();
    if (codes.length === 0) {
      e.preventDefault();
      alert('Pick at least one category before subscribing.');
    }
  });
}
```

The orphan `const status` and `const submitBtn` (L202–203) are also unused — drop them.

### C2 — Broken nav links in `confirm_expired.html` and `unsubscribed.html`

- `confirm_expired.html` L27: `href="Landing Page.html#subscribe"` → should be `/#subscribe`
- `confirm_expired.html` L28: `href="Landing Page.html"` → should be `/`
- `unsubscribed.html` L25: same problem → `/#subscribe`
- `unsubscribed.html` L26: same → `/`

These are leftover from the handoff HTML files where `Landing Page.html` was a preview-friendly placeholder for the landing route. The handoff README §3.2 explicitly says: "Swap those for `{{ url_for('landing') }}#today`". Easiest is plain `/`.

### C3 — `manage.html` footer "Manage" link points to `#`

`manage.html` L138: `<a href="#">Manage</a>`. Should be `{{ url_for('manage') }}?token={{ token }}` (or just the current URL).
Same nit in `privacy.html` L76 (`<a href="#">Privacy</a>` instead of `/privacy`) and `form.html` L153 (`<a href="#">Manage subscription</a>` inside the preview-card footer mock — this one is mocked content, so it's defensible, but should at minimum be a non-functional `<span>`).

### C4 — `_digest_preview.html` is stale

The `/preview` route (`subscriptions/main.py:219`) still renders `_digest_preview.html`, which uses class names that don't exist in the new `app.css`:

- `.preview-card-header`, `.preview-card-eyebrow`, `.preview-card-title`, `.preview-card-meta`
- `.preview-card-section-label`, `.preview-card-paper`, `.preview-card-paper-number`
- `.preview-fallback-note`

The new CSS uses `.pv-head` / `.pv-masthead` / `.pv-h1` / `.pv-issue` / `.pv-pick-label` / `.pv-paper` / `.pv-paper-num` / `.pv-omitted`. `/preview` therefore renders an article with an essentially unstyled body.

Two options:
1. **Kill `/preview`** — the handoff README §3.4 says it's "superseded by the editions switcher" inside the landing. Remove the route + `_load_preview()` + `_digest_preview.html` + the `public_digest_preview.json` plumbing.
2. **Rewrite the partial** against the `.pv-*` system. Then have `form.html` include it (`{% include '_digest_preview.html' %}`) inside `<article class="preview-card">` so the landing and the standalone `/preview` page share one source of truth.

Recommend option 1 unless the standalone view has a real use (e.g. linked from outside the app).

---

## Design improvements (per `frontend-design`)

### D1 — Hero hierarchy reads slightly off

Right now the hero (form.html L11–42) renders in this order: eyebrow → italic kicker → display headline → italic deck → marginalia → lead → reply-demo box → CTAs. That's a lot of italics stacked before the lead and the CTA. With `body.hero-deck-on`, the eyebrow is also display-none'd (CSS L1349), so the user sees italic-italic-display-italic-marginalia-lead — five voices competing before the CTA.

**Suggestion**: keep either the kicker OR the deck line, not both. The deck-line is more informative ("An editorial weekly daily, machine-built and editor-curated by you…") and earns its space; the kicker ("In which the morning's research is cut to size · — · No. 03") is a vanity flourish that delays the lead. If you must keep both, drop the marginalia in this slot — it's a third voice before the user has read the lead.

### D2 — The reply-demo box is mono and visually heavy where a sentence would do

`.reply-demo` (CSS L316–342) is a chunky 4-line monospace card sitting between the lead and the CTAs. It steals attention from the primary CTA. In Stratechery / The Browser the equivalent would be a single italic line. Consider making it a single hairline-underlined inline gloss under the lead, e.g.:

> *Reply with the numbers (`1 3 5`) and the PDFs come back attached in ~30 s.*

Then keep the elaborated 3-cell flow inside `#reply-section` (which is already in the markup but hidden via `body[data-reply-demo="off"]`). One showcase per concept, not two.

### D3 — Section-heading right-aligned `.section-sub` is a meta-label, not a deck — give it dignity

`.section-heading .section-sub` (CSS L265–271) is `text-xs`, muted, letter-spaced. Today it carries content like "four sample mornings · real arXiv data" and "double opt-in · free · no tracking" — those are actually trust signals worth reading. At `--text-xs` with `0.08em` letter-spacing they vanish.

**Suggestion**: bump to `--text-sm`, no letter-spacing, italic serif, color `--text-muted`. Treat it as a deck under the eyebrow, not as legal fine print.

### D4 — Editions switcher meta wraps awkwardly between 540px and ~720px

`.editions-switcher` (CSS L1261–1316) is a flex row with `.es-label · .es-chips · .es-meta` (margin-left auto). At narrow widths the `.es-meta` text "4 sample mornings · real papers, real dates" wraps under the chips with `margin-left: 0; width: 100%` — but only at ≤540px. Between 540px and ~720px it sits tight against the last chip with no breathing room. Add `flex: 1 1 auto` or bump the breakpoint.

### D5 — `.cat-option` hover background extends edge-to-edge of cat-list

`.cat-option:hover { background: var(--accent-soft); }` (CSS L866) is good, but the row has no left/right padding past the checkbox grid track. The hover band feels chopped. Add `padding: 0.35em var(--space-3)` (currently `var(--space-2)`) for the hover hit area; alternatively round it (`border-radius: var(--radius-sm)`) which already exists at L861 — but the surrounding container needs a hair of padding to let the rounded hit area breathe.

### D6 — `.preset.clear` styling is fine but disjoint

`.preset.clear` is rendered as a pill that turns red on hover (CSS L715–716). It's stylistically identical to other presets, which makes "Clear all" feel like another preset bundle. Either:
- Move "Clear all" outside the pill row (a subtle text link to the right of the pills — there's already `body.clear-subtle-on` styling for exactly this at L1433–1444, but the body class isn't applied), or
- Give it a visibly different shape (no border, underlined text).

The CSS already supports option 1. Add `clear-subtle-on` to the `<body>` class in `_base.html` if you want to ship it.

### D7 — Mobile preview-card readability

On mobile (`@media (max-width: 880px)`) the preview card is forced flat (`transform: none !important`), and the `.pv-pick-num` shrinks from 3.8rem to 3rem (L1243) — but `.pv-h1` only drops from 2rem to 1.5rem (L1242). The 60px-tall Editor's-Pick numeral on mobile fights the 24px title for visual weight. Drop `.pv-pick-num` to ~2.4rem on mobile, or push the title to 1.7rem so the proportions match the desktop ratio.

### D8 — Focus states pass `:focus-visible` test, but mouse-only hover on `.es-chip` is invisible

`.es-chip:hover` (L1296) changes border-color and text color from neutral to amber. On a dark background with already-amber-bordered active chips, the hover delta on inactive chips reads as ~5% brighter — easy to miss. Add a subtle background lift: `background: var(--surface);` on hover, `var(--accent-soft)` would also work and aligns with the cat-option hover language.

### D9 — Editorial coherence with the email digest

The web preview card and `digest/templates/digest.html` share the palette and the editor's-pick layout. Two small drifts:
- The web preview's Editor's Pick numeral (`.pv-pick-num`, 3.8rem L490) uses `--paper-accent-soft` (`#e6bc85`). The email's equivalent is `#e6bc85` inline — same value, good.
- The web preview's tag (`.pv-tag`, L511–522) is black-on-cream pill, font-weight 600; the email's same tag inlines `background:#1a1a1a;color:#f4f1ea` with no font-weight (defaults). Tiny weight mismatch; align both to 600 for consistency.

The bigger drift is that the **email never shows the postmark SVG**, the tilt, or the `letter-card-on` shadow. That's fine — those are web-only "this is what you'll receive" cues. Just make sure the brief team is OK that the email has no postmark.

---

## Architectural improvements (per `frontend-patterns`)

### A1 — Extract `.folio`, `.colophon`, `.full-footer` into `_base.html`

Right now every child template (`form.html`, `manage.html`, `confirm_ok.html`, `confirm_expired.html`, `unsubscribed.html`, `privacy.html`, `terms.html`) duplicates:

```html
<div class="folio" aria-hidden="true">
  <span>...{{ today_label }}</span>
  <span class="right">{{ surface_label }}</span>   <!-- only this varies -->
</div>
...
<div class="colophon">
  <strong>Colophon</strong>
  Set in Georgia, with system sans...     <!-- identical everywhere -->
</div>

<footer class="full-footer">
  ...                                      <!-- identical except <li>Manage</li> href -->
</footer>
```

That's ~50 lines × 7 templates = ~350 lines of pure duplication. Move all three into `_base.html`, expose a single `{% block surface_label %}{% endblock %}` for the folio's right text, and a `{% block footer_manage_href %}/#subscribe{% endblock %}` for the one Manage-link variant. Each child template drops ~50 lines.

### A2 — `_base.html` needs the blocks the brief mentions

The handoff README §5 spec'd `{% block og_title %}` / `{% block og_description %}` / `{% block twitter_title %}` / `{% block twitter_description %}`. These exist in `_base.html` L12–17, good. But:

- `manage.html`, `confirm_ok.html`, `confirm_expired.html`, `unsubscribed.html`, `privacy.html`, `terms.html` **never override any of them**. So Google/Twitter previews for every surface say "your morning briefing of new research". That's fine for landing; surface-specific is better. Add overrides per page.
- `{% block og_image %}` is missing entirely. `og-image.png` is also missing from `static/`. Brief calls this out (handoff §15) as an explicit gap to fill.

### A3 — Drop the entire `.tweaks-panel` CSS block

`app.css` L1450–1627 (≈177 lines, ~5.5 KB raw, ~1.5 KB gzipped) is design-time tooling. No HTML references it (`grep` confirms zero matches in templates for `tweaks-panel`, `tweak-toggle`, etc.). The handoff README §6 Option A says "strip it entirely". Delete the block.

Also drop the now-orphan focus-visible selectors at `app.css` L676–679 (`.tweak-toggle:focus-visible`, `.tweak-radio button:focus-visible`, `.tweaks-close:focus-visible`, `.tweaks-foot button:focus-visible`).

### A4 — Tweak body classes are baked, but `body.marginalia-on` and `body.clear-subtle-on` aren't applied

The body has `letter-card-on folio-on hero-deck-on section-ornament-on chips-on cap-inline-on full-footer-on`. That matches the handoff README §6's "user landed on this combination" list except for two omissions:

- **`marginalia-on`** is intentionally off — the marginalia spans inside `form.html` (L23, L51, L223, L332) render as `display: none` everywhere ≤1180px (which is most viewports). Either turn it on if you want sidenotes ≥1180px (and accept the narrowed main column at L1361), or strip the `<aside class="marginalia">` blocks from the templates entirely. Right now they exist as dead markup at any viewport <1180px.
- **`clear-subtle-on`** — see D6 above.

Either commit to the variants or remove the supporting CSS + markup. Today they're Schrödinger components.

### A5 — Inline `style="…"` is heavy on confirm/unsubscribe/expired

27 inline-style attributes across the three short templates. Examples:
- `confirm_ok.html` L17–24: 8 inline styles to assemble the "What you signed up for" status block.
- `confirm_expired.html` L17–24: similar pattern for the error explainer.
- `unsubscribed.html` L17–22: same.

These should be extracted into named components — e.g. `.welcome-card`, `.welcome-card-cats`, `.welcome-card-meta`, `.error-card-list`. The selectors are ad-hoc enough that an `_includes/_welcome_card.html` partial would clean up confirm_ok and let you reuse it later.

### A6 — Specificity discipline is mostly good; two `!important`s are tolerable

`grep -c "!important" app.css` = 2 occurrences, both in mobile overrides:
- L1250 `body.letter-card-on .preview-wrap { transform: none !important; margin-right: 0 !important; }` — overriding a more-specific tweak rule, defensible.
- L1388 `body.marginalia-on .marginalia { display: none !important; }` — same.

Neither is a smell. Keep.

### A7 — JS organization: vanilla IIFE-ish is fine for this scope, but…

`app.js` is ~465 lines, single file, top-level `const` declarations (no IIFE wrapper). That's fine for a static site. Two things to clean up:

1. **The whole file should be wrapped in an IIFE or a `{}` block** to avoid leaking `PRESETS`, `catList`, `renderEdition`, etc. into `window`. Right now they're all globals. Trivial fix: wrap L1–465 in `(() => { ... })();`.
2. **The GitHub IIFE is already isolated** (L358–463) — good model. The rest of the file should follow it.
3. **`SAMPLE_EDITIONS` (L226–299, ~74 lines of data)** could move to a `data-editions` JSON attribute on the editions-switcher container, or a separate `sample-editions.json` fetched once. Today it's bundled into every page load even on `/manage`, `/privacy`, etc. where it's never used. Better: gate the whole editions-switcher block + its data behind `if (document.getElementById('pv-papers')) { ... }`.

### A8 — `data-screen-label` attributes on sections look like leftover design-tool annotation

`form.html` L45, L170, L217, L326, L358 each have `data-screen-label="01 Today"`, `data-screen-label="01.5 Reply flow"`, etc. Nothing in `app.js` reads them. Likely a remnant of the handoff designer's authoring tool. Safe to delete; no behavior change.

### A9 — `.eyebrow` is set to `display: none` when `hero-deck-on`, but the template still renders it

`form.html` L12 `<p class="eyebrow">A daily briefing for researchers</p>` is always painted, then hidden by `body.hero-deck-on .eyebrow { display: none }` (L1349). Cheap. But other surfaces (confirm_ok, confirm_expired, unsubscribed, manage, privacy) **do** want the eyebrow visible — and they ALSO inherit `hero-deck-on` from the body class baked into `_base.html`. Check: yes, `confirm_ok.html` L11 `<p class="eyebrow">Confirmed · welcome</p>` is being hidden by `hero-deck-on`. **This is a real bug**: every non-landing surface has its eyebrow display:none'd.

**Fix**: change `body.hero-deck-on .eyebrow { display: none }` to a hero-scoped rule: `body.hero-deck-on .hero > .eyebrow { display: none }`. Only the landing hero swaps the eyebrow for the kicker/deck combo; other surfaces keep theirs.

### A10 — `request.url` in `og:url` includes scheme + query string

`_base.html` L14: `<meta property="og:url" content="{{ request.url }}">`. On `https://localhost/?some_tracker=foo` this surfaces the query string. Preferable: strip query and fragment server-side, or use `{{ request.url.replace(query=None) }}` / build it from `request.base_url + request.url.path`.

---

## Dead code or inconsistencies — safe to delete or unify

| What | Where | Action |
|---|---|---|
| Whole tweaks-panel CSS block | `app.css` L1452–1627 | Delete |
| `.tweaks-*` selectors in `:focus-visible` group | `app.css` L676–679 | Delete |
| `const status` / `const submitBtn` orphan vars | `app.js` L202–203 | Delete |
| Duplicate `const form` declaration | `app.js` L201 | Delete (keep L208) |
| `data-screen-label` attrs on `<section>`s | `form.html` L45, L170, L217, L326, L358 | Delete |
| `.colophon` block duplicated in 7 templates | every child template | Move to `_base.html` |
| `.full-footer` block duplicated in 7 templates | every child template | Move to `_base.html` |
| `.folio` block duplicated in 7 templates | every child template | Move to `_base.html` |
| `Landing Page.html` href leftovers | `confirm_expired.html` L27–28, `unsubscribed.html` L25–26 | Fix to `/` |
| `<a href="#">` placeholders | `manage.html` L138, `privacy.html` L76 | Real URLs |
| Stale `_digest_preview.html` classnames | the whole partial | Rewrite or kill `/preview` |
| `<aside class="marginalia">` blocks | `form.html` L23, L51, L223, L332 | Either turn on `marginalia-on` and accept the narrow main, or strip these blocks |

---

## Component checklist (DESIGN_BRIEF anti-patterns + landing best-practices)

Per DESIGN_BRIEF.md L190–206 and common editorial-landing practice:

- [x] No gradient blobs, no glassmorphism, no glass tiles
- [x] No emoji in UI (Unicode arrows `→ ↓ ←` and `❦` flourish are intentional)
- [x] No fake social proof — GitHub star count is real and progressive
- [x] No `#000` — `--bg: #13161a`
- [x] No sans-serif headlines — all `h1`/`h2`/`h3` are Georgia via `app.css` L72–78
- [x] No scroll-triggered interrupts, no modal popups, no auto-playing media
- [x] No "Revolutionize your…" / no exclamation marks / no rocket emoji
- [x] Single chromatic accent (amber `#d99c5e`); danger/success only on `.status`
- [x] Editorial, understated copy in the brief's voice
- [x] All form `name=` attributes preserved (`email`, `categories`, `keywords`, `max_papers`)
- [x] All JS hook IDs preserved (`#cat-search`, `#cat-list`, `#presets`, `#submit-btn`, `#selected-count`, `#cap-inline-input`, `#max_papers`)
- [x] All `data-*` hooks preserved (`data-preset-id`, `data-search`, `data-edition`, `data-target`)
- [ ] **`og:image` (1200×630 PNG) — missing**; handoff README §15 flagged this
- [ ] **CSP header — not configured**; recommend `default-src 'self'` plus `connect-src 'self' https://api.github.com` for the GitHub fetch
- [ ] **`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`** — confirm these are set in the FastAPI middleware or Caddy config
- [ ] **`loading="lazy"` on below-the-fold images** — N/A, no `<img>` tags. Good.
- [ ] **`<title>` per surface** — landing, manage, confirm_ok, confirm_expired, unsubscribed, privacy, terms each override `{% block title %}` correctly. Good.
- [ ] **`og_title` / `og_description` per surface** — only the landing's base value renders for every surface. Override per page.
- [ ] **Eyebrow visible on non-landing surfaces** — currently hidden by `hero-deck-on`. See A9.
- [ ] **`/preview` renders correctly** — currently broken; see C4.

---

## Priority queue

Ordered by impact / effort.

1. **Fix `const form` duplication in `app.js`** — 30-second one-line edit; restores 100% of client-side interactivity. (C1)
2. **Fix `Landing Page.html` hrefs in confirm_expired + unsubscribed** — two-minute find/replace; unbreaks navigation. (C2)
3. **Fix `.eyebrow` being display:none on non-landing surfaces** — scope the selector to `.hero > .eyebrow` inside the landing's body class, or add a `landing-only` body class to `form.html`. (A9)
4. **Decide `/preview`: kill or rewrite `_digest_preview.html`** — 15 minutes either way; eliminates a broken public surface. (C4)
5. **Strip `.tweaks-panel` dead CSS (~180 lines)** — cleanup; 1.5 KB gzipped saving and removes confusion. (A3)
6. **Extract `.folio` / `.colophon` / `.full-footer` into `_base.html` blocks** — kills ~350 lines of duplication across 7 templates; future template changes become one-place edits. (A1)
7. **Override `og_title` / `og_description` per surface + add `static/og-image.png`** — better social previews; addresses handoff README §15 gap.
8. **Either commit `marginalia-on` (and accept narrowed main) or strip the `<aside class="marginalia">` blocks** — eliminates Schrödinger components. (A4)
9. **Wrap `app.js` in an IIFE; gate `SAMPLE_EDITIONS` + renderer behind landing-only check** — stops leaking 30+ globals, stops shipping ~5 KB of unused sample-editions data to every non-landing page. (A7)
10. **Polish: hero-deck or hero-kicker (not both); promote `.section-sub` from fine-print to deck-like; bump `.cat-option` hover padding** — small visual wins per D1, D3, D5.

---

End of review.
