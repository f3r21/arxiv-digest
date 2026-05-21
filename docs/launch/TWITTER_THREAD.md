# Twitter / X thread draft — The Daily Abstract

> Voice reference: `docs/BRAND_VOICE.md`. Editorial, understated, concrete.
> No emoji, no "🚀", no "Excited to announce..." or "Today I'm launching".
> Tweets max ~280 chars each.
>
> Suggested cadence: post one tweet, 30s pause, post next. Manual thread.

---

## Tweet 1 (the hook)

I built a daily arXiv newsletter you can *reply to* for the PDFs.

You pick categories. At 7am you get an edition. Reply "1 3 5" and three
PDFs come back as attachments, ~30 seconds later.

Free, open source, $0/month forever.

https://arxivdaily.ignorelist.com

## Tweet 2

The reply-to-PDF flow is the part I've never seen elsewhere.

Mailsac inbox + a 30-line Python listener that polls every 10 minutes,
maps the sender to the subscriber's last digest, downloads the requested
arXiv PDFs, attaches them, sends back via Brevo.

No clicking through tabs.

## Tweet 3

Optional Spanish translation of title + abstract via MyMemory's free tier
(~23k chars/day, well inside the 50k cap).

500M Spanish-speaking researchers and no major arXiv tool targets them.
Latam in particular.

The originals are one click away.

## Tweet 4

The whole stack runs on Oracle Cloud's always-free tier — one AMD
E2.1.Micro VM, 1 GB RAM. The six Docker containers (subscriptions,
digest, listener, translator, Caddy, MailHog for dev) idle at ~165 MB
total.

Self-hosting your own copy: docker compose up.

## Tweet 5

There's a public archive at /archive — every past edition by category,
permanently linkable. RSS feeds per category. Grows automatically as the
daily digest runs.

The bet: high-specificity long-tail discovery (search for "new
distributed systems papers May 2026").

## Tweet 6 (CTA)

Subscribe at https://arxivdaily.ignorelist.com

Repo MIT-licensed: https://github.com/f3r21/arxiv-digest

It's a side project, an indie publication that happens to be software.
Feedback welcome — especially from researchers who actually live in
arXiv every day.
