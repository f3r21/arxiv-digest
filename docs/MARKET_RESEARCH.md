# Market Research: Personalized arXiv Discovery for Researchers

**Subject product:** The Daily Abstract (https://arxivdaily.ignorelist.com)
**Date:** May 2026
**Audience:** Internal positioning document for The Daily Abstract going from 1 → 1,000+ users.

---

## Executive Summary

- The category has split into three lanes: **funded incumbents** (alphaXiv, Scite, Researcher app), **free academic projects** (Scholar Inbox, Semantic Scholar Research Feeds, arxiv-sanity-lite), and **broadcast newsletters** (TLDR AI, AlphaSignal, Import AI, The Batch). The Daily Abstract competes in lane #2 but with a UX (email-only, reply-to-PDF) that no incumbent ships.
- The "free + email digest + arXiv-specific" slot is now anchored by **Scholar Inbox** (free, academic, multi-archive). That is the most direct functional competitor. They optimize for ML-rated relevance; we optimize for low-friction control (categories + keywords + reply-PDF + Spanish).
- **No mainstream tool offers reply-to-email-for-PDF**, none target **Spanish-speaking researchers** as a primary persona, and **none are both open source and self-hostable**. These are three real, defensible gaps.
- alphaXiv ($7M seed, Nov 2025, Menlo Ventures + Schmidt/Thrun angels) is the funded threat — but it is positioned as "GitHub of AI research" (social + interactive), not email-first daily digest. They will not contract our niche.
- Launch venues that work in this category: **Hacker News** (avg +289 GitHub stars in week 1 for AI tooling launches), **r/MachineLearning**, **arXiv-sanity successor communities**, and Spanish-language ML Twitter / r/MachineLearningEspanol for the Latam wedge.

---

## Direct Competitors

| Product | Mechanic (1 sentence) | Pricing | Scale | Differentiator | Audience | Strengths | Gaps |
|---|---|---|---|---|---|---|---|
| **Scholar Inbox** | Free daily/weekly email of ML-ranked papers, trained on user thumbs up/down. | Free | "Used by thousands of scientists" (ACL 2025 demo paper); growing since HN launch late 2023. | ML-rated relevance from active learning; indexes arXiv + bioRxiv + medRxiv + ChemRxiv + CS proceedings. | Academic researchers across hard sciences. | Multi-archive coverage, visual summaries, academic credibility (CVPR/MPI group). | Closed source; English-only; cold-start friction (must rate papers); no reply-to-PDF; no keyword filters as primary interface. |
| **arxiv-sanity-lite** | TF-IDF + SVM "more like this" UI over arXiv. | Free / OSS | 1.6k GitHub stars; community fork live at arxiv-sanity.org. | Karpathy's legacy brand; pure tagging UX. | CS/ML PhD-era researchers. | Open source, brand recognition. | **Karpathy stopped maintaining March 2025**; no email digest as primary surface; English-only; UI is dated; relies on community to keep alive. |
| **alphaXiv** | Social/interactive layer on top of arXiv — comments, AI Q&A, "blog" mode for papers. | Free tier + paid (paid tier specifics not public as of seed announcement); $7M seed Nov 2025 (Menlo Ventures, Haystack, Schmidt, Thrun). | "Millions of users" claim post-launch 2024. | Funded; positioned as "GitHub of AI research"; interactive paper experience. | AI researchers + practitioners. | Capital, brand momentum, AI-native paper interaction, Eric Schmidt halo. | Not an email-digest product; depends on user actively visiting; English-only; not OSS. |
| **Semantic Scholar Research Feeds** | Save papers to library folders → AI recommends similar new papers via email. | Free (Allen Institute / non-profit). | Embedded inside Semantic Scholar's 200M+ paper graph. | Backed by AI2; uses SPECTER-style embeddings; covers all of science, not just arXiv. | Cross-discipline researchers. | Free forever, institutional backing, semantic-quality recs. | UX requires building a library first (cold-start); no keyword-as-filter primitive; no reply-PDF; recommendations are a feature inside a bigger product, not the headline experience. |
| **Emergent Mind** | AI research explorer over arXiv with summaries, Q&A, social-signal trending. | Free: 10 articles/week. **Pro: $10/mo annual, $12/mo monthly.** | Smaller — primarily a single-operator product with prosumer pricing. | Tracks social engagement (Twitter/GitHub/YouTube) per paper, video summaries. | CS/AI researchers + curious technical readers. | Trending signal is novel; paid tier is cheap. | Article cap on free tier is harsh; not an email-first product; English-only. |
| **Connected Papers** | Graph-of-related-papers visualization from a seed paper. | Free: 5 graphs/mo. **Academic: $3/mo annual. Business: $10/mo annual.** | Long-standing brand in the space (~since 2020). | Visual graph UX is iconic and hard to copy quickly. | Researchers doing literature reviews. | Strong brand, fair pricing, scholarship program. | Not a discovery feed — you must already know one paper; no email/digest; no notion of "today's new arXiv". |
| **Researcher app** (researcher-app.com) | Mobile-first feed of new papers from 20k+ sources, with keyword/author feeds + notifications. | Free (institutional partnerships). | **2.1M users** claimed. | Mobile UX + breadth across journals/preprints. | Broad academia, not arXiv-specific. | Largest claimed user base in this list. | Mobile-app-first, not email-first; CS/ML is one of many verticals; reportedly noisy. |
| **AutoLLM/ArxivDigest** (and forks: rivercold, linhkid, gkahn13) | OSS Python repos that pull arXiv, score with GPT/Claude/Gemini, optionally email via SendGrid. | Free / DIY-OSS | Hundreds of stars across forks. | Closest **functional match** to our product surface. | Self-hosters / tinkerer ML researchers. | Already validates demand for our exact UX. | Requires LLM API budget; user must self-host; no UX for non-technical subscribers; no Spanish; no reply-PDF; no shared infra. |

---

## Adjacent Products (Solve a Related Need, Not Direct)

- **TLDR AI** — 1.25M+ daily subscribers; broadcast, not personalized; framed as "news," not "papers." Different content, same inbox slot.
- **AlphaSignal** — ~200k subscribers; daily AI/ML curated by humans (Lior Sinclair); strong with practitioner-researchers. Broadcast, not per-user filtered.
- **Import AI** (Jack Clark) — 127k+ subscribers, ~$10/mo paid tier; weekly essay + paper analysis; thought-leader play, not a filter.
- **The Batch** (DeepLearning.AI / Andrew Ng) — weekly, broadcast, no public subscriber number but very large. Brand-driven.
- **Hugging Face Daily Papers** — 12k+ email subscribers; curated by @akhaliq; no personalization.
- **Paper Digest** (paperdigest.org) — daily arXiv summaries, broader/older brand, lower-frequency engagement signals.
- **Scite** — $20/mo personal ($12/mo annual). Citation-context tool, not discovery, but competes for the "research tooling" wallet.
- **Connected Papers** — see above; literature-review tool, not daily intake.

---

## Market Gaps (Aligned With Our Differentiators)

| Differentiator we ship | Anyone else doing it? | Verdict |
|---|---|---|
| **Reply-to-email for PDF attachments** | None of the 8 direct competitors. AutoLLM/ArxivDigest forks ship HTML emails with download links, not reply-PDF. | **Real, defensible gap.** Email-as-interface is rare in this category. |
| **Spanish translation of title + abstract** | None. Scholar Inbox, alphaXiv, S2, arxiv-sanity all English-only. | **Real gap, especially for Latam.** Specifically zero arXiv-translation newsletters surfaced for LATAM in the search. |
| **Open source + self-hostable** | arxiv-sanity-lite (unmaintained); the AutoLLM/ArxivDigest fork family (DIY only). | **Partial gap.** OSS exists but nothing is "OSS + production-grade + free service for non-technical users" simultaneously. |
| **Per-user keyword filters as the headline primitive** | Researcher app has keyword feeds. AutoLLM uses natural-language interests. Scholar Inbox uses ratings, not keywords. | **Partial gap.** Keyword-first (vs ML-rating-first) is a real philosophical split — yours is more transparent and faster to set up. |
| **AI relevance scoring on top of arXiv** | Scholar Inbox (yes), AutoLLM ArxivDigest (yes, via LLM), Emergent Mind (yes). | **NOT a gap.** Several incumbents do this. Don't lead with it. |
| **$0/mo infra (always-free tier stack)** | None advertise this. | **Gap as a story, not as a feature.** Matters for credibility/trust ("we won't disappear when funding dries up"), not as user-visible value. |

**Best gap to wedge into:** the intersection of **reply-PDF UX** + **Spanish/LATAM** + **OSS trust signal**. Each alone is small; together they are a defensible micro-positioning that nobody else holds.

---

## Pricing Intelligence

Direct paper-discovery tools cluster in three pricing patterns:

- **Free forever, no paid tier:** Scholar Inbox, Semantic Scholar, Hugging Face Papers, arxiv-sanity. These are funded by research grants or platforms.
- **Freemium with cheap pro tier ($3–$12/mo):** Connected Papers ($3 academic / $10 business), Emergent Mind ($10–12/mo). This is the realistic monetization band for an indie tool.
- **Mid-priced productivity tools ($12–20/mo):** Scite, ResearchRabbit-adjacent. These bundle citation analysis + writing aids.
- **Newsletter sponsorships:** TLDR AI / AlphaSignal / Import AI monetize via sponsored slots (typical CPM range $50–$150 for premium dev/AI audiences; paid Substack adds ~$10/mo paid tier).

**Implication for The Daily Abstract:** If/when monetizing, the realistic price ceiling for "personal" tier is $5–10/mo (Connected Papers anchors $3 academic, Emergent Mind anchors $10). Above $12 you compete with full-stack tools (Scite, Researcher pro). A "support the project" donation model ($3–5/mo) plus optional Spanish/Latam university institutional tier is more defensible than a feature-gated freemium ladder, given Scholar Inbox and Semantic Scholar are free competitors.

---

## Launch Strategy Hints

**Empirical baseline:** Recent arXiv paper (Nov 2025) tracking 138 AI-tool HN launches in 2024–2025 found average gains of **+121 stars at 24h, +189 at 48h, +289 at one week** after HN exposure. "Show HN" tag was *not* a statistically significant driver after controls — what matters is timing (post-launch hour) and headline quality.

Recommended venue sequence:

1. **Hacker News "Show HN"** — primary launch. Title should lead with the most novel concrete mechanic (reply-PDF), not with "another arXiv newsletter." Aim for a Tue/Wed morning US Pacific slot. Reference: Karpathy and Scholar Inbox both surfaced this way.
2. **r/MachineLearning** weekly self-promotion / "[P]roject" threads — secondary, lower-volume but high-quality signups.
3. **Latam-specific channels** — r/MachineLearningEspanol, ML Twitter/X in Spanish (Pablo Samuel Castro, Juliana Negrini, etc.), DCC universities mailing lists (UChile, UNAM, UBA, USP). This is unique surface area that no English-only competitor will work.
4. **Hugging Face community thread** — there is already an open thread asking "would a curated daily AI digest be useful?" with engagement, indicating warm audience.
5. **Substack cross-posting** — mirror the digest as a public archive on Substack to harvest organic search and Substack-internal discovery.
6. **Direct outreach to OSS ML educators** — Karpathy's audience is now orphaned from arxiv-sanity-lite. A clean "spiritual successor, with email" pitch resonates.

Avoid Product Hunt as a primary launch — wrong audience (consumer/PM), low conversion for academic tooling.

---

## Risks

- **Scholar Inbox** is the most dangerous competitor: free, academic credibility, ACL 2025 demo paper, daily email, multi-archive. If they add Spanish or reply-PDF, our wedge narrows. **Mitigation:** ship the wedge features (reply-PDF, Spanish) before they do, lean into OSS as a trust signal they cannot copy without changing their model.
- **alphaXiv** has the capital and brand momentum to add a digest product as a feature. **Mitigation:** their roadmap reads as "interactive paper experience," not "daily email." Watch for blog posts about email features; expect ~12 months before they would credibly threaten the email-digest niche.
- **Semantic Scholar Research Feeds** is free, well-funded by AI2, and improving. The reason it has not crushed niche tools is its onboarding (build a library first) — but if they add keyword-first onboarding, the gap closes.
- **arxiv-sanity-lite community fork** (arxiv-sanity.org) could be resurrected by a credible maintainer at any time and reclaim mindshare.
- **AutoLLM/ArxivDigest fork family** is functionally similar enough that someone could productize one of these forks with reply-PDF + Spanish in a weekend. The moat is execution speed + audience trust, not technology.
- **arXiv API rate limiting** (already a known risk per repo MEMORY: export.arxiv.org has hard-blocked the prod IP) — a competitor with better infra/caching could outperform us on reliability. Worth investing in robust caching before scale.
- **Email deliverability ceiling** on free tiers (Brevo, Mailsac) — at 1k+ subscribers, the always-free stack will need a paid sender. Plan migration path now.

---

## Recommendation

Position The Daily Abstract as: **"The free, open-source daily arXiv digest. In your language. Just hit reply for the PDF."**

Lead messaging with the three things nobody else does together: **reply-PDF**, **Spanish**, **OSS/self-hostable**. De-emphasize AI relevance scoring (Scholar Inbox and Emergent Mind already own that narrative). Launch on Hacker News with reply-PDF as the headline mechanic, then immediately follow with Spanish-language channels to build a defensible regional beachhead before alphaXiv or Scholar Inbox notice.

---

## Sources

- https://github.com/karpathy/arxiv-sanity-lite (status of arxiv-sanity-lite, issue #23 "Taking over the project")
- https://siliconangle.com/2025/11/19/alphaxiv-raises-7m-funding-become-github-ai-research/ (alphaXiv $7M seed)
- https://www.prnewswire.com/news-releases/alphaxiv-raises-7m-seed-round-to-bridge-the-ai-research-to-practice-divide-302619615.html
- https://alphasignal.ai/ + https://alphasignal.ai/AlphaSignal_media_kit.pdf (AlphaSignal scale)
- https://www.emergentmind.com/pricing (Emergent Mind pricing — $10–12/mo Pro, 10 articles/wk free)
- https://www.connectedpapers.com/pricing (Connected Papers — $3 academic / $10 business annual)
- https://www.semanticscholar.org/faq/what-are-research-feeds (S2 Research Feeds)
- https://scite.ai/pricing (Scite — $12/mo annual personal)
- https://arxiv.org/abs/2504.08385 + https://aclanthology.org/2025.acl-demo.30/ (Scholar Inbox ACL 2025 demo paper)
- https://scholar-inbox.com/
- https://importai.substack.com/ + Jack Clark X post on 100k subscribers crossed
- https://www.deeplearning.ai/the-batch (The Batch)
- https://tldr.tech/ai (TLDR AI — 1.25M subscribers claim)
- https://huggingface.co/papers + https://huggingface.co/blog/daily-papers (HF Daily Papers — 12k subscribers)
- https://github.com/AutoLLM/ArxivDigest
- https://github.com/rivercold/Personalized-Arxiv-digest
- https://github.com/gkahn13/arxiv-filter
- https://github.com/iai-group/arXivDigest
- https://arxiv.org/abs/2511.04453 (Launch-Day Diffusion: HN impact on AI-tool GitHub stars, 2024–2025)
- https://researcher-app.com / https://discovery.researcher.life/ (Researcher app + R Discovery user base)
- https://info.arxiv.org/help/subscribe.html + https://blog.arxiv.org/2022/05/05/readers-can-now-opt-in-to-personalized-email-alerts/ (arXiv native subscription baseline)
