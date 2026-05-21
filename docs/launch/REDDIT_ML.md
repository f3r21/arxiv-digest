# Reddit /r/MachineLearning draft — The Daily Abstract

> Subreddit: r/MachineLearning. Flair: **[Project]**.
> Voice: same as BRAND_VOICE.md but with a slight technical bias (audience
> is ML practitioners, not journalists). Reddit allows markdown so we can
> use headers and bullets.

---

**Title:**
> [P] The Daily Abstract — a free arXiv newsletter with reply-to-email for PDFs

**Body:**

I've been drowning in arXiv. Skimming the daily feed of ~200 cs.LG papers
takes longer than I'd like, and the "let me save this PDF for later"
ritual involves too many clicks. So I built a tool that fixes both.

## What it does

- You pick your arXiv categories (with optional keyword filters and a
  daily cap)
- At 7am each morning you get an email with the new papers that match
- **Reply with paper numbers ("1 3 5") and the PDFs come back as
  attachments**, usually within thirty seconds
- Titles and abstracts are translated to Spanish (optional, originals one
  link away — but the project explicitly targets Spanish-speaking
  researchers who are underserved by English-only tools)
- One-click manage subscription / unsubscribe via signed token links in
  every email

## Why post here

I want feedback from researchers who actually live in arXiv. Specifically:

- **Does the reply-for-PDF flow solve a real pain or am I scratching my
  own itch?** I've found no other tool doing this. Curious whether the
  reply-as-interface feels natural or weird.
- **Filtering preferences**: the current model is categories + optional
  keyword OR. AI relevance scoring (LLM-judged) is on the roadmap but
  haven't implemented yet — would that meaningfully improve the digest,
  or is keyword OR good enough?
- **Open source angle**: would you self-host instead of subscribing to
  the public instance? The whole stack is on a free-tier VM, so I'd want
  to know if "indie public service" is a credible model here.

## Stack (for the curious)

Open source, MIT: https://github.com/f3r21/arxiv-digest

- **Web**: FastAPI + Jinja templates + vanilla JS (no React)
- **Email out**: Brevo SMTP (free tier, 300/day)
- **Email in (replies)**: Mailsac inbox + polling listener
- **Translation**: MyMemory free tier (~50k chars/day cap)
- **HTTPS**: Caddy with auto Let's Encrypt
- **Hosting**: Oracle Cloud always-free (AMD E2.1.Micro, 1 GB RAM, 6
  Docker containers idle at ~165 MB total)
- **Cost**: $0/month indefinitely

The whole architecture is six containers in `docker-compose.yml`. The
trickiest piece was the digest pipeline: fetch arXiv once per morning
(union of all subscribers' categories — single HTTP call regardless of
N subscribers), then filter per-subscriber in memory. The translator
microservice has a text-keyed cache so a paper appearing in N subscriber
digests is translated once.

## Public archive

There's a permanent /archive at https://arxivdaily.ignorelist.com/archive
— every past edition by category, with RSS feeds. Currently grows
automatically as the daily digest runs.

## Subscribe

https://arxivdaily.ignorelist.com — double opt-in, no tracking, no
analytics, no ads.

Happy to answer questions about the architecture or design choices.

---

*Mods: this is a self-promotion post for a free open-source project I built,
not a commercial product. Per subreddit rules I'm flairing as [P] / Project.*
