"""The Daily Abstract - servicio de suscripciones (FastAPI).

Double opt-in: POST /subscribe -> email con token -> GET /confirm activa.
Edit profile: GET/POST /manage?token=...
"""

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Annotated, AsyncIterator

from email_validator import EmailNotValidError, validate_email
from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import archive_repo
import categories_catalog as cats
import db
import email_outbound
import tokens

logger = logging.getLogger("subscriptions")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s INIT: %(message)s",
)

PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
SUBSCRIBE_RATE_PER_HOUR = int(os.environ.get("SUBSCRIBE_RATE_PER_HOUR", "5"))
DISPOSABLE_BLOCKLIST = {
    d.strip().lower()
    for d in os.environ.get("DISPOSABLE_DOMAIN_BLOCKLIST", "").split(",")
    if d.strip()
}
MAX_KEYWORDS = 30

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
DATA_DIR = Path("/app/data")
PUBLIC_PREVIEW_PATH = DATA_DIR / "public_digest_preview.json"
PREVIEW_CACHE_TTL_S = 300  # 5 min

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup: init DB, catalog, seed; shutdown: nada que cerrar."""
    db.init_db()
    cats.load()
    seed_from_env()
    logger.info("INIT: subscriptions arrancado; base_url=%s", PUBLIC_BASE_URL)
    yield


app = FastAPI(title="The Daily Abstract", lifespan=lifespan)
app.state.limiter = limiter
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(_request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": "rate_limit_exceeded", "detail": str(exc.detail)},
    )


# === Quick presets para la landing ===
# IDs coinciden con `data-preset-id` en las templates (Claude Design handoff).
# Es solo UI/cliente: el server valida individualmente cada codigo.
PRESETS = [
    {"id": "ml", "label": "Machine Learning", "codes": ["cs.LG", "cs.AI", "stat.ML", "cs.NE"]},
    {"id": "distsys", "label": "Distributed Systems", "codes": ["cs.DC", "cs.OS", "cs.NI", "cs.SY"]},
    {"id": "theory", "label": "Theory", "codes": ["cs.CC", "cs.DS", "cs.IT", "cs.GT", "math.CO"]},
    {"id": "nlp", "label": "NLP", "codes": ["cs.CL", "cs.IR"]},
    {"id": "cv", "label": "Computer Vision", "codes": ["cs.CV"]},
    {"id": "sec", "label": "Security", "codes": ["cs.CR"]},
    {"id": "robotics", "label": "Robotics", "codes": ["cs.RO", "cs.SY"]},
]


def seed_from_env() -> None:
    """Crea automaticamente el suscriptor seed desde RECIPIENT (compat)."""
    email = os.environ.get("RECIPIENT", "").strip().lower()
    if not email or email.endswith("@local"):
        return
    if db.find_by_email(email):
        return
    seed_cats_raw = os.environ.get("SEED_SUBSCRIBER_CATEGORIES", "cs.DC").split(",")
    seed_cats = cats.validate_codes([c for c in seed_cats_raw if c.strip()])
    seed_kws = [
        k.strip()
        for k in os.environ.get("SEED_SUBSCRIBER_KEYWORDS", "").split(",")
        if k.strip()
    ]
    if not seed_cats:
        logger.warning("WARN: SEED_SUBSCRIBER_CATEGORIES vacio o invalido; no seed")
        return
    sub_id = db.insert_subscriber(
        email=email,
        categories=seed_cats,
        keywords=seed_kws[:MAX_KEYWORDS],
        max_papers=15,
        source="seed",
    )
    logger.info(
        "INIT: seed subscriber %s id=%d categories=%s",
        email, sub_id, seed_cats,
    )


def _today_label() -> str:
    return date.today().strftime("%d %b %Y")


def _common_ctx(request: Request, **extra) -> dict:
    """Context compartido para todos los templates (masthead, footer, etc.).

    `canonical_url` se construye respetando PUBLIC_BASE_URL (no `request.url`,
    que detras de un reverse proxy resuelve al hostname interno y rompe los
    previews de OG/Twitter cards).
    """
    canonical_url = f"{PUBLIC_BASE_URL}{request.url.path}"
    return {
        "request": request,
        "today_label": _today_label(),
        "canonical_url": canonical_url,
        "public_base_url": PUBLIC_BASE_URL,
        **extra,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt() -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /confirm\n"
        "Disallow: /manage\n"
        "Disallow: /unsubscribe\n"
        "Disallow: /admin/\n"
        "Disallow: /health\n"
        "Disallow: /categories.json\n"
        "Disallow: /presets.json\n"
        "\n"
        f"Sitemap: {PUBLIC_BASE_URL}/sitemap.xml\n"
    )


@app.get("/sitemap.xml")
def sitemap_xml() -> Response:
    base = PUBLIC_BASE_URL
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        f'  <url><loc>{base}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>',
        f'  <url><loc>{base}/privacy</loc><changefreq>monthly</changefreq><priority>0.3</priority></url>',
        f'  <url><loc>{base}/terms</loc><changefreq>monthly</changefreq><priority>0.3</priority></url>',
        f'  <url><loc>{base}/archive</loc><changefreq>daily</changefreq><priority>0.8</priority></url>',
    ]
    for category, _n in archive_repo.list_categories():
        lines.append(
            f'  <url><loc>{base}/archive/{category}</loc><changefreq>daily</changefreq><priority>0.7</priority></url>'
        )
        for date_str in archive_repo.list_editions(category):
            lines.append(
                f'  <url><loc>{base}/archive/{category}/{date_str}</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>'
            )
    lines.append("</urlset>")
    return Response(content="\n".join(lines) + "\n", media_type="application/xml")


@app.get("/categories.json")
def categories_json() -> list[dict[str, str]]:
    return cats.load()


@app.get("/presets.json")
def presets_json() -> list[dict]:
    return PRESETS


@app.get("/", response_class=HTMLResponse)
def form_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "form.html",
        _common_ctx(
            request,
            grouped_categories=cats.grouped(),
            selected_codes=set(),  # ninguna pre-seleccionada en la landing
        ),
    )


# === Preview pipeline ===

_preview_cache: dict | None = None
_preview_cache_at: float = 0.0
_PREVIEW_MOCK: dict = {
    "issue": None,
    "sent_at": None,
    "is_mock": True,
    "papers": [
        {
            "arxiv_id": "2510.12345",
            "title": "Linear-Time Attention via Structured State Spaces",
            "authors": ["A. Researcher", "B. Coauthor"],
            "abstract": "We present a transformer architecture that scales linearly with sequence length, evaluated on language modeling benchmarks with competitive perplexity.",
            "match_reason": "transformer",
        },
        {
            "arxiv_id": "2510.67890",
            "title": "Federated Scheduling for Edge Kubernetes Clusters",
            "authors": ["C. Author"],
            "abstract": "A control-plane design that coordinates pod placement across geographically distributed edge nodes with sub-100ms latency targets.",
            "match_reason": "kubernetes",
        },
        {
            "arxiv_id": "2510.13579",
            "title": "Sparse-Reward Reinforcement Learning Without Shaping",
            "authors": ["D. Researcher"],
            "abstract": "We propose an intrinsic motivation signal that allows agents to learn from sparse rewards without engineered reward shaping, with SOTA results on Atari.",
            "match_reason": "reinforcement learning",
        },
    ],
}


def _load_preview() -> dict:
    """Lee public_digest_preview.json con cache; fallback a mockup."""
    global _preview_cache, _preview_cache_at
    now = time.time()
    if _preview_cache is not None and (now - _preview_cache_at) < PREVIEW_CACHE_TTL_S:
        return _preview_cache
    data: dict
    try:
        raw = PUBLIC_PREVIEW_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not data.get("papers"):
            data = _PREVIEW_MOCK
    except (FileNotFoundError, json.JSONDecodeError):
        data = _PREVIEW_MOCK
    # truncar a top 3 para la landing
    data = dict(data)
    data["papers"] = list(data.get("papers") or [])[:3]
    _preview_cache = data
    _preview_cache_at = now
    return data


@app.get("/preview", response_class=HTMLResponse)
def preview_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "_digest_preview.html",
        _common_ctx(request, preview=_load_preview(), standalone=True),
    )


# === Subscribe (existente, sin cambios funcionales) ===


def _parse_keywords(raw: str) -> list[str]:
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()][:MAX_KEYWORDS]


def _validate_email_or_400(raw_email: str) -> str:
    try:
        info = validate_email(
            raw_email, check_deliverability=False, test_environment=True
        )
    except EmailNotValidError as exc:
        raise HTTPException(status_code=400, detail=f"email invalido: {exc}")
    normalized = info.normalized.lower()
    domain = normalized.rsplit("@", 1)[-1]
    if domain in DISPOSABLE_BLOCKLIST:
        raise HTTPException(status_code=400, detail="dominio no permitido")
    return normalized


@app.post("/subscribe")
@limiter.limit(f"{SUBSCRIBE_RATE_PER_HOUR}/hour")
async def subscribe(
    request: Request,
    email: Annotated[str, Form()],
    categories: Annotated[list[str], Form()] = [],
    keywords: Annotated[str, Form()] = "",
    max_papers: Annotated[int, Form()] = 15,
) -> JSONResponse:
    ip = get_remote_address(request)
    email_norm = _validate_email_or_400(email)
    db.log_subscribe_attempt(ip, email_norm)

    valid_cats = cats.validate_codes(categories)
    if not valid_cats:
        raise HTTPException(
            status_code=400,
            detail="elige al menos una categoria valida",
        )
    if len(valid_cats) > 20:
        raise HTTPException(status_code=400, detail="maximo 20 categorias")
    kws = _parse_keywords(keywords)
    max_p = max(1, min(int(max_papers), 30))

    payload = {
        "categories": valid_cats,
        "keywords": kws,
        "max_papers": max_p,
    }
    token = tokens.make_confirm_token(email_norm)
    db.store_pending(tokens.hash_token(token), email_norm, payload, ip)

    try:
        email_outbound.send_confirmation(email_norm, token, valid_cats)
    except Exception as exc:
        logger.error("ERROR: confirm email fallo para %s: %s", email_norm, exc)
        raise HTTPException(status_code=502, detail="no se pudo enviar el email")

    return JSONResponse(
        {"status": "pending_confirmation", "email": email_norm},
        status_code=202,
    )


@app.get("/confirm", response_class=HTMLResponse)
def confirm(request: Request, token: Annotated[str, Query()]) -> HTMLResponse:
    email = tokens.read_confirm_token(token)
    if not email:
        return templates.TemplateResponse(
            "confirm_expired.html",
            _common_ctx(request),
            status_code=400,
        )
    pending = db.pop_pending(tokens.hash_token(token))
    if pending is None:
        return templates.TemplateResponse(
            "confirm_expired.html",
            _common_ctx(request),
            status_code=400,
        )
    payload = pending["payload"]
    sub_id = db.insert_subscriber(
        email=email,
        categories=list(payload.get("categories") or []),
        keywords=list(payload.get("keywords") or []),
        max_papers=int(payload.get("max_papers") or 15),
        source="web",
    )
    logger.info("RESULT: confirm OK %s id=%d", email, sub_id)
    manage_url = f"{PUBLIC_BASE_URL}/manage?token={tokens.make_manage_token(sub_id)}"
    subscriber = db.get_subscriber_by_id(sub_id)
    return templates.TemplateResponse(
        "confirm_ok.html",
        _common_ctx(
            request,
            email=email,
            categories=payload.get("categories") or [],
            subscriber=subscriber,
            manage_url=manage_url,
        ),
    )


# === Unsubscribe (existente, sin cambios funcionales) ===


def _do_unsubscribe(token: str) -> int | None:
    sub_id = tokens.read_unsubscribe_token(token)
    if sub_id is None:
        return None
    sub = db.get_subscriber_by_id(sub_id)
    if sub is None:
        return None
    db.soft_delete_subscriber(sub_id)
    logger.info("RESULT: unsubscribed id=%d email=%s", sub_id, sub.email)
    return sub_id


@app.get("/unsubscribe", response_class=HTMLResponse)
def unsubscribe_get(
    request: Request, token: Annotated[str, Query()]
) -> HTMLResponse:
    sub_id = _do_unsubscribe(token)
    if sub_id is None:
        return templates.TemplateResponse(
            "confirm_expired.html",
            _common_ctx(request),
            status_code=400,
        )
    return templates.TemplateResponse(
        "unsubscribed.html", _common_ctx(request)
    )


@app.post("/unsubscribe")
def unsubscribe_post(token: Annotated[str, Query()]) -> JSONResponse:
    """One-click List-Unsubscribe-Post handler (RFC 8058)."""
    sub_id = _do_unsubscribe(token)
    if sub_id is None:
        return JSONResponse({"status": "invalid_token"}, status_code=400)
    return JSONResponse({"status": "unsubscribed"})


# === Manage subscription ===


@app.get("/manage", response_class=HTMLResponse)
def manage_get(
    request: Request, token: Annotated[str, Query()], saved: int = 0
) -> HTMLResponse:
    sub_id = tokens.read_manage_token(token)
    if sub_id is None:
        return templates.TemplateResponse(
            "confirm_expired.html",
            _common_ctx(request),
            status_code=400,
        )
    sub = db.get_subscriber_by_id(sub_id)
    if sub is None or db.find_by_email(sub.email) is None:
        # exists pero esta unsubscribed
        return templates.TemplateResponse(
            "confirm_expired.html",
            _common_ctx(request),
            status_code=400,
        )
    unsub_token = tokens.make_unsubscribe_token(sub_id)
    return templates.TemplateResponse(
        "manage.html",
        _common_ctx(
            request,
            subscriber=sub,
            selected_codes=set(sub.categories),
            keywords_str=", ".join(sub.keywords),
            grouped_categories=cats.grouped(),
            token=token,
            unsubscribe_url=f"{PUBLIC_BASE_URL}/unsubscribe?token={unsub_token}",
            saved=bool(saved),
        ),
    )


@app.post("/manage", response_class=HTMLResponse)
async def manage_post(
    request: Request,
    token: Annotated[str, Query()],
    categories: Annotated[list[str], Form()] = [],
    keywords: Annotated[str, Form()] = "",
    max_papers: Annotated[int, Form()] = 15,
) -> HTMLResponse:
    sub_id = tokens.read_manage_token(token)
    if sub_id is None:
        return templates.TemplateResponse(
            "confirm_expired.html",
            _common_ctx(request),
            status_code=400,
        )
    valid_cats = cats.validate_codes(categories)
    if not valid_cats:
        raise HTTPException(
            status_code=400,
            detail="elige al menos una categoria valida",
        )
    if len(valid_cats) > 20:
        raise HTTPException(status_code=400, detail="maximo 20 categorias")
    kws = _parse_keywords(keywords)
    max_p = max(1, min(int(max_papers), 30))
    updated = db.update_subscription_for(sub_id, valid_cats, kws, max_p)
    if not updated:
        return templates.TemplateResponse(
            "confirm_expired.html",
            _common_ctx(request),
            status_code=400,
        )
    logger.info(
        "RESULT: manage update id=%d cats=%s kws=%s max=%d",
        sub_id, valid_cats, kws, max_p,
    )
    # Redirect via 303 a GET con saved=1 (PRG pattern)
    return RedirectResponse(url=f"/manage?token={token}&saved=1", status_code=303)


# === Legal pages ===


@app.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("privacy.html", _common_ctx(request))


@app.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("terms.html", _common_ctx(request))


# === Admin debug ===


# === Archive ===


_CATEGORY_NAMES: dict[str, str] = {}


def _category_name(code: str) -> str:
    """Lookup human-readable category name (cached)."""
    if not _CATEGORY_NAMES:
        for e in cats.load():
            _CATEGORY_NAMES[e["code"]] = e["name"]
    return _CATEGORY_NAMES.get(code, code)


@app.get("/archive", response_class=HTMLResponse)
def archive_index(request: Request) -> HTMLResponse:
    """Index general: lista de categorias con archive, agrupadas por arXiv group."""
    cats_with_counts = archive_repo.list_categories()
    grouped: dict[str, list[dict]] = {}
    catalog_lookup = {e["code"]: e for e in cats.load()}
    for code, n in cats_with_counts:
        entry = catalog_lookup.get(code, {"code": code, "name": code, "group": "Other"})
        group = entry["group"]
        grouped.setdefault(group, []).append(
            {"code": code, "name": entry["name"], "count": n}
        )
    return templates.TemplateResponse(
        "archive_index.html",
        _common_ctx(request, grouped_archive=grouped, total_categories=len(cats_with_counts)),
    )


@app.get("/archive/{category}", response_class=HTMLResponse)
def archive_category(request: Request, category: str) -> HTMLResponse:
    """Lista chronologica de ediciones para una categoria."""
    if not cats.is_valid_code(category):
        raise HTTPException(status_code=404, detail="unknown arXiv category")
    dates = archive_repo.list_editions(category)
    if not dates:
        # Categoria valida pero sin archive (aun)
        return templates.TemplateResponse(
            "archive_category.html",
            _common_ctx(
                request,
                category=category,
                category_name=_category_name(category),
                editions=[],
            ),
            status_code=200,
        )
    # Cargar preview (titulo paper #1) de cada edicion para listing
    editions = []
    for d in dates:
        ed = archive_repo.load_edition(category, d)
        if ed is None:
            continue
        editions.append(
            {
                "date": d,
                "issue": ed.issue,
                "paper_count": len(ed.papers),
                "first_title": ed.papers[0]["title"] if ed.papers else "",
            }
        )
    return templates.TemplateResponse(
        "archive_category.html",
        _common_ctx(
            request,
            category=category,
            category_name=_category_name(category),
            editions=editions,
        ),
    )


@app.get("/archive/{category}/feed.xml")
def archive_feed(category: str) -> Response:
    """Atom feed: ultimas N ediciones de la categoria."""
    if not cats.is_valid_code(category):
        raise HTTPException(status_code=404, detail="unknown arXiv category")
    base = PUBLIC_BASE_URL
    cat_name = _category_name(category)
    dates = archive_repo.list_editions(category, limit=20)
    entries: list[str] = []
    for d in dates:
        ed = archive_repo.load_edition(category, d)
        if ed is None:
            continue
        title = f"The Daily Abstract — {category} — {d}"
        permalink = f"{base}/archive/{category}/{d}"
        # Build a short HTML summary
        summary_lines = [f"<p>{len(ed.papers)} papers in {category} for {d}.</p><ol>"]
        for p in ed.papers[:10]:
            t = (p.get("title") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            arxiv_id = p.get("arxiv_id", "")
            summary_lines.append(
                f'<li>{t} — <a href="https://arxiv.org/abs/{arxiv_id}">arxiv:{arxiv_id}</a></li>'
            )
        summary_lines.append("</ol>")
        summary = "".join(summary_lines).replace("]]>", "]]&gt;")
        entries.append(
            f'<entry>\n'
            f'  <title>{title}</title>\n'
            f'  <link href="{permalink}"/>\n'
            f'  <id>{permalink}</id>\n'
            f'  <updated>{ed.generated_at or d + "T00:00:00Z"}</updated>\n'
            f'  <summary type="html"><![CDATA[{summary}]]></summary>\n'
            f'</entry>'
        )
    updated = dates[0] + "T00:00:00Z" if dates else "1970-01-01T00:00:00Z"
    feed_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        f'  <title>The Daily Abstract — {cat_name} ({category})</title>\n'
        f'  <link href="{base}/archive/{category}"/>\n'
        f'  <link rel="self" href="{base}/archive/{category}/feed.xml"/>\n'
        f'  <id>{base}/archive/{category}</id>\n'
        f'  <updated>{updated}</updated>\n'
        f'  <subtitle>Daily archive of new arXiv papers in {category}.</subtitle>\n'
        + "\n".join(entries)
        + '\n</feed>\n'
    )
    return Response(content=feed_xml, media_type="application/atom+xml")


@app.get("/archive/{category}/{date_str}", response_class=HTMLResponse)
def archive_edition(
    request: Request, category: str, date_str: str
) -> HTMLResponse:
    """Edicion completa: lista de papers para esa (categoria, fecha).

    IMPORTANTE: este route va DESPUES de /archive/{category}/feed.xml para
    que feed.xml no se interprete como {date_str}.
    """
    if not cats.is_valid_code(category):
        raise HTTPException(status_code=404, detail="unknown arXiv category")
    ed = archive_repo.load_edition(category, date_str)
    if ed is None:
        raise HTTPException(status_code=404, detail="edition not found")
    return templates.TemplateResponse(
        "archive_edition.html",
        _common_ctx(
            request,
            category=category,
            category_name=_category_name(category),
            date_str=ed.date_str,
            issue=ed.issue,
            papers=ed.papers,
        ),
    )


@app.get("/admin/subscribers", response_class=JSONResponse)
def list_subs_for_debug() -> list[dict]:
    """Endpoint debug: lista suscriptores activos. NO exponer en prod sin auth."""
    if os.environ.get("EXPOSE_ADMIN", "0") != "1":
        raise HTTPException(status_code=404, detail="not found")
    return [
        {
            "id": s.id,
            "email": s.email,
            "categories": s.categories,
            "keywords": s.keywords,
            "max_papers": s.max_papers,
        }
        for s in db.list_active()
    ]
