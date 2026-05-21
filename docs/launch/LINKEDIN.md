# LinkedIn post draft — The Daily Abstract

> Audience: research-adjacent folks in your professional network (alumni,
> profesores, ex-compañeros de carrera, gente de la industria que toca ML).
> Voice: same editorial tone but LinkedIn-readable (slightly more
> professional framing). No emoji per BRAND_VOICE.md.

---

I built a small thing this month: **The Daily Abstract**, a daily
arXiv newsletter for academic researchers.

Two features I couldn't find anywhere else, combined:

→ Reply to the email with paper numbers, get the PDFs as attachments.
The digest arrives at 7am with the day's new papers in your chosen
categories. Reply "1 3 5" and three PDFs come back, attached, in about
thirty seconds. No tab juggling.

→ Titles and abstracts translated to Spanish. Optional, originals are
one click away. There are roughly 500 million Spanish-speaking
researchers and no major arXiv tool targets them — this is a small
attempt to fix that.

Open source under MIT. Runs on Oracle Cloud's always-free tier — one
1 GB RAM VM, six Docker containers, ~$0/month indefinitely. The whole
codebase is here: github.com/f3r21/arxiv-digest

There's a public archive at /archive growing automatically as each
daily digest runs. RSS feeds per arXiv category. Long-tail discovery
play.

It's an indie publication that happens to be software. Not a startup,
no investors, no ads. Just a tool I wanted to exist.

If you're a researcher who lives in arXiv, give it a try and tell me
what's broken: https://arxivdaily.ignorelist.com

#arXiv #MachineLearning #AcademicResearch #OpenSource
