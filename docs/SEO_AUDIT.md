# SEO Audit: The Daily Abstract

Auditoria generada por el agente `seo-specialist` sobre el deploy live
(`https://arxivdaily.ignorelist.com`) + render local en `https://localhost/`.

## Critical Issues

```text
[CRITICAL] No robots.txt — site is effectively uncrawl-configured
Location: https://arxivdaily.ignorelist.com/robots.txt (404)
Issue: Without robots.txt, crawlers have no directives and Google cannot
       discover a sitemap. FastAPI returns a JSON 404 from its own router,
       which Googlebot correctly treats as a missing file. This is not a
       crawl blocker on its own but means you have zero control over what
       crawlers index (e.g., /confirm, /manage, /unsubscribe are currently
       indexable if linked to).
Fix: Add robots.txt as a FastAPI static file or a dedicated route. See
     "Suggested robots.txt" below.
```

```text
[CRITICAL] No sitemap.xml
Location: https://arxivdaily.ignorelist.com/sitemap.xml (404)
Issue: No sitemap means Google relies entirely on link discovery. With only
       a handful of public URLs the risk is low, but the sitemap is also
       the correct place to declare canonical URLs and signal update
       frequency, which matters once /archive grows.
Fix: Register /sitemap.xml as a route in main.py. See "Suggested sitemap.xml"
     at end.
```

```text
[CRITICAL] og:url renders as http://localhost/ in production
Location: subscriptions/templates/_base.html
Issue: <meta property="og:url" content="{{ request.url }}"> resolves to the
       raw FastAPI request URL. When running behind Caddy with
       X-Forwarded-Proto forwarded, FastAPI still uses the internal hostname
       unless PUBLIC_BASE_URL is explicitly injected into the template.
       Social crawlers cache http://localhost/ as the canonical OG URL,
       poisoning share previews permanently.
Fix: In _common_ctx(), add "canonical_url": PUBLIC_BASE_URL + str(request.url.path)
     and replace {{ request.url }} with {{ canonical_url }} in the template.
```

```text
[CRITICAL] No <link rel="canonical"> on any page
Location: subscriptions/templates/_base.html — missing entirely
Issue: Without canonical tags, if the site is ever reachable on both http://
       and https://, or on both ignorelist.com subdomain and a future custom
       domain, Google will split PageRank across duplicate URLs.
Fix: <link rel="canonical" href="{{ canonical_url }}">
```

## High-Impact Opportunities

```text
[HIGH] No og:image or twitter:image — social share cards are text-only
Fix: Create a 1200×630 og-image.png. Add to _base.html:
       <meta property="og:image" content="{{ canonical_base }}/static/og-image.png">
       <meta name="twitter:image" content="..."/>
       <meta name="twitter:card" content="summary_large_image">
```

```text
[HIGH] Secondary pages inherit the homepage meta description verbatim
Location: privacy.html, terms.html, manage.html
Fix: Add {% block description %} overrides per template.
```

```text
[HIGH] No JSON-LD structured data on any page
Issue: Zero structured data. Missing WebSite, FAQPage, Organization schema.
Fix: See "Suggested Structured Data" section.
```

```text
[HIGH] X-Frame-Options header missing from Caddy config
Fix: Add to caddy/Caddyfile header block: X-Frame-Options "DENY"
```

```text
[HIGH] No keyword targeting in heading copy
Issue: H1 is "New arXiv papers, hand-cut to your interests." Body copy has
       phrases like "arXiv newsletter", "personalized arXiv digest" but never
       in headings (which crawlers weight heavily).
Fix: Change eyebrow on form.html to "Free arXiv newsletter for researchers".
     H2 "Subscribe" → "Subscribe to your personalized arXiv digest".
```

```text
[HIGH] Broken internal links in unsubscribed.html (FIXED)
Location: subscriptions/templates/unsubscribed.html:25,26
Fix: replaced "Landing Page.html" → "/"
```

```text
[HIGH] Self-referencing footer link on privacy.html points to "#" not "/privacy"
Location: privacy.html:76 and terms.html:66
Fix: Replace href="#" with href="/privacy" / href="/terms"
```

## Medium / Nice-to-Have

```text
[MEDIUM] Preview card h2 ("Hoy en arXiv") inside <article> nests wrong
Location: form.html — <h2 class="pv-h1">
Fix: Change to <p class="pv-h1"> (visual styling unchanged; semantic-clean).
```

```text
[MEDIUM] /manage /confirm /unsubscribe should be Disallowed in robots.txt
Fix: See robots.txt below.
```

```text
[MEDIUM] CSS is 46 KB uncompressed — within budget, but only gzip enabled
Location: caddy/Caddyfile: "encode gzip"
Fix: If Caddy build supports brotli, "encode zstd gzip" or "encode br gzip"
     (15-20% better compression).
```

```text
[MEDIUM] No <link rel="alternate" type="application/rss+xml"> for future archive
Fix: When /archive ships:
     <link rel="alternate" type="application/rss+xml" title="The Daily Abstract"
           href="/archive/feed.xml">
```

```text
[MEDIUM] "Quick presets" label has no for= association
Location: form.html — bare <label class="form-label"> wrapping no input
Fix: Wrap presets in a <fieldset> with a <legend>:
       <fieldset>
         <legend class="form-label">Quick presets</legend>
         <div class="presets" id="presets">...</div>
       </fieldset>
```

---

## Suggested Structured Data (JSON-LD)

Add to `_base.html` inside `<head>`:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": "https://arxivdaily.ignorelist.com/#website",
      "url": "https://arxivdaily.ignorelist.com/",
      "name": "The Daily Abstract",
      "description": "A personalized daily arXiv newsletter for academic researchers.",
      "inLanguage": "en"
    },
    {
      "@type": "Organization",
      "@id": "https://arxivdaily.ignorelist.com/#org",
      "name": "The Daily Abstract",
      "url": "https://arxivdaily.ignorelist.com/",
      "sameAs": ["https://github.com/f3r21/arxiv-digest"]
    }
  ]
}
</script>
{% block jsonld %}{% endblock %}
```

**form.html — FAQPage block** (add at bottom of `{% block content %}`):

```html
{% block jsonld %}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What does The Daily Abstract cost?",
      "acceptedAnswer": {"@type":"Answer","text":"Nothing. The whole stack runs on Oracle Cloud's always-free tier. The basic digest stays free, forever."}
    },
    {
      "@type": "Question",
      "name": "How does the reply-to-PDF feature work?",
      "acceptedAnswer": {"@type":"Answer","text":"Every digest is sent with Reply-To pointing at a monitored inbox. Reply with the paper numbers you want; the PDFs come back as email attachments, usually within thirty seconds."}
    },
    {
      "@type": "Question",
      "name": "Who runs The Daily Abstract?",
      "acceptedAnswer": {"@type":"Answer","text":"An indie open-source project, MIT-licensed, self-hostable. No company, no investors, no ads."}
    },
    {
      "@type": "Question",
      "name": "How do I cancel my subscription?",
      "acceptedAnswer": {"@type":"Answer","text":"Every email has a one-click unsubscribe link in the footer, plus a List-Unsubscribe header. You can also reply STOP."}
    }
  ]
}
</script>
{% endblock %}
```

---

## Suggested robots.txt

Add to `main.py`:

```python
from fastapi.responses import PlainTextResponse

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt() -> str:
    return """User-agent: *
Allow: /
Disallow: /confirm
Disallow: /manage
Disallow: /unsubscribe
Disallow: /admin/
Disallow: /health
Disallow: /categories.json
Disallow: /presets.json

Sitemap: https://arxivdaily.ignorelist.com/sitemap.xml
"""
```

---

## Suggested sitemap.xml

```python
from fastapi.responses import Response

@app.get("/sitemap.xml")
def sitemap_xml() -> Response:
    base = PUBLIC_BASE_URL
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{base}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>
  <url><loc>{base}/privacy</loc><changefreq>monthly</changefreq><priority>0.3</priority></url>
  <url><loc>{base}/terms</loc><changefreq>monthly</changefreq><priority>0.3</priority></url>
</urlset>"""
    return Response(content=xml, media_type="application/xml")
```

---

## Long-Term Strategy: The Digest Archive

The single largest SEO opportunity is a **public archive of past digests**.

**Route pattern:** `/archive/{category}/{YYYY-MM-DD}` — e.g.,
`/archive/cs.LG/2026-05-20`.

"arxiv newsletter cs.LG" and "new machine learning papers May 2026" are
genuinely searched phrases. Category-scoped daily archive pages have high
keyword specificity, naturally accumulate internal links, and grow
passively with zero editorial effort.

**Schema per archive page:**

```json
{
  "@type": "BlogPosting",
  "headline": "Attention Is All You Need",
  "author": {"@type": "Person", "name": "Vaswani et al."},
  "datePublished": "2026-05-20",
  "url": "https://arxivdaily.ignorelist.com/archive/cs.LG/2026-05-20#1706.03762",
  "isPartOf": {"@type": "Blog", "name": "The Daily Abstract — cs.LG digest"}
}
```

Internal linking from homepage: "Today's edition" links per-edition to
`/archive/cs.LG/{today}` etc. Seeds PageRank flow immediately.

RSS feed: `/archive/cs.LG/feed.xml` for feed readers and Google News.

Index page: `/archive` as table of contents by category.

---

## Priority Queue

| Priority | Issue | File |
|---|---|---|
| Critical | No robots.txt | Add route to `main.py` |
| Critical | No sitemap.xml | Add route to `main.py` |
| Critical | og:url renders as localhost | `_base.html`, `_common_ctx()` |
| Critical | No canonical tag | `_base.html` |
| High | No og:image / twitter:image | `_base.html` + static asset |
| High | Duplicate meta descriptions | privacy.html, terms.html, manage.html |
| High | No JSON-LD structured data | `_base.html`, `form.html` |
| High | Missing X-Frame-Options | `caddy/Caddyfile` |
| High | Headings not targeting core phrases | `form.html` eyebrow + h2 |
| High | Footer self-links #' on privacy/terms | privacy.html:76, terms.html:66 |
| ✅ FIXED | Broken hrefs in unsubscribed.html | unsubscribed.html, confirm_expired.html |
| Medium | pv-h1 should be `<p>` not `<h2>` | form.html |
| Medium | /manage /confirm /unsubscribe robots Disallow | robots.txt (new) |
| Medium | Brotli compression | caddy/Caddyfile |
| Medium | Presets label group missing fieldset/legend | form.html |
