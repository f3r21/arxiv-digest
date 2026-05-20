"""arXiv Daily - servicio de suscripciones (FastAPI).

Double opt-in: POST /subscribe -> email con token -> GET /confirm activa.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, AsyncIterator

from email_validator import EmailNotValidError, validate_email
from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

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


app = FastAPI(title="arxiv-digest subscriptions", lifespan=lifespan)
app.state.limiter = limiter
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(_request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": "rate_limit_exceeded", "detail": str(exc.detail)},
    )


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/categories.json")
def categories_json() -> list[dict[str, str]]:
    return cats.load()


@app.get("/", response_class=HTMLResponse)
def form_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "grouped_categories": cats.grouped(),
            "all_categories_json": json.dumps(cats.load()),
        },
    )


def _parse_keywords(raw: str) -> list[str]:
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()][:MAX_KEYWORDS]


def _validate_email_or_400(raw_email: str) -> str:
    """Valida sintaxis del email.

    `test_environment=True` permite dominios reservados (@local, @example.com)
    para dev/demo. En prod no hace falta restringirlos: si el dominio no
    existe el SMTP de salida fallara igual y nunca se llega a confirmar.
    """
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
            {"request": request},
            status_code=400,
        )
    pending = db.pop_pending(tokens.hash_token(token))
    if pending is None:
        return templates.TemplateResponse(
            "confirm_expired.html",
            {"request": request},
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
    return templates.TemplateResponse(
        "confirm_ok.html",
        {"request": request, "email": email, "categories": payload.get("categories") or []},
    )


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
            {"request": request},
            status_code=400,
        )
    return templates.TemplateResponse(
        "unsubscribed.html", {"request": request}
    )


@app.post("/unsubscribe")
def unsubscribe_post(token: Annotated[str, Query()]) -> JSONResponse:
    """One-click List-Unsubscribe-Post handler (RFC 8058)."""
    sub_id = _do_unsubscribe(token)
    if sub_id is None:
        return JSONResponse({"status": "invalid_token"}, status_code=400)
    return JSONResponse({"status": "unsubscribed"})


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
