# Show HN draft — The Daily Abstract

> Voice reference: `docs/BRAND_VOICE.md` — editorial, understated, concrete,
> no exclamation marks, no emoji. Pulir antes de postear.
>
> Posting tip per `MARKET_RESEARCH.md`: format "Show HN: X" no diferencia
> estadisticamente; el contenido es lo que importa. Posteable en cualquier
> dia, idealmente 7-9am ET.

---

**Title** (max 80 chars HN):
> Show HN: The Daily Abstract — a free arXiv newsletter you can reply to for PDFs

**URL field:**
> https://arxivdaily.ignorelist.com

**Body** (HN post text):

I built a daily arXiv newsletter that does two things I couldn't find
elsewhere together:

1. **Reply with paper numbers to get the PDFs.** The digest arrives at 7am
   with N new papers in your chosen categories. Reply "1 3 5" and the PDFs
   come back as attachments, usually within thirty seconds. No clicking
   through six tabs.

2. **Titles and abstracts translated to Spanish.** Optional; the English
   versions are one link away. There aren't many tools serving Spanish-
   speaking researchers without making them pay or use a US-only product.

It's free, open source under MIT, and the whole stack runs on Oracle Cloud's
always-free tier (one ARM E2.1.Micro VM, ~165 MB of RAM idle for 6 Docker
containers). The math: ~$0/month forever, assuming the free tier remains.

Tech stack:
- FastAPI + Jinja for the web surfaces
- A separate FastAPI microservice wrapping MyMemory (free translation API,
  50k chars/day)
- A digest service that fetches arXiv once per morning (union of all
  subscriber categories — one HTTP call regardless of how many users) and
  filters per-subscriber in memory
- A listener that polls Mailsac (free inbox API) for replies, parses
  numbers, downloads PDFs from arXiv, attaches them, sends back via Brevo
- Caddy in front for automatic HTTPS via Let's Encrypt
- SQLite (WAL) for state, no external DB

The whole thing is in one repo: https://github.com/f3r21/arxiv-digest

The archive at /archive is public and grows passively as the daily digest
runs — every category's edition gets a permanent URL with the day's papers.
That's the SEO bet: high-specificity long-tail queries like "new
distributed systems papers May 2026" should land here.

Happy to answer questions about the architecture, the choice to keep
everything stateless-ish, or how the reply-to-PDF flow handles a multi-user
inbox (the Mailsac inbox is single but the listener maps each reply's
From: to a subscriber).

---

**If asked "Why arXiv-sanity exists"**: Karpathy's tool is great for
browsing but doesn't do email digests or reply-for-PDFs. The Daily Abstract
is closer to "newsletter format" than "search tool". Both can coexist.

**If asked "Why translate to Spanish"**: roughly 500M Spanish speakers, no
major arXiv tool targets them. Latin American researchers are a real
underserved audience and the translation is essentially free.

**If asked "Will it stay free"**: yes, for the basic digest. If there's
ever signal for a pro tier (AI relevance scoring, multi-source ingestion),
that would be paid. But the core feature stays free.

**If asked "How does email-as-interface scale"**: a single Mailsac inbox
handles all replies; we map sender→subscriber via DB lookup. Mailsac free
tier is 1500 polls/month, well above what's needed at moderate scale.
