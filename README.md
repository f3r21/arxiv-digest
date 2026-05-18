# arxiv-digest

Sistema deterministico que envia digests diarios de papers nuevos en arxiv a tu inbox. Respondes con numeros, te llegan los PDFs.

## Levantar

```bash
docker compose up -d --build
docker compose ps
```

MailHog UI: http://localhost:8025

## Trigger manual del digest

```bash
docker compose exec digest python -c "from main import run_digest; run_digest()"
```

## Editar el filtro

Edita `filters.yml`. Tras editar, no hace falta rebuild — el digest lo lee en cada corrida.

## Apagar

```bash
docker compose down       # mantiene volumenes
docker compose down -v    # borra todo
```
