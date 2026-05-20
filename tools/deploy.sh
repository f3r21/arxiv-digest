#!/usr/bin/env bash
# Deploy de arxiv-digest a un servidor remoto (Oracle Cloud, VPS, etc.).
# Usa imagenes pre-built desde Docker Hub (no compila en la VM).
#
# Uso (en el SERVIDOR, despues de clonar el repo):
#   cp .env.prod.example .env.prod
#   # editar .env.prod con valores reales (incluido DOCKERHUB_USER)
#   ./tools/deploy.sh
#
# Para publicar nuevas imagenes: en la laptop, ./tools/build_and_push.sh
# (despues, en la VM, ./tools/deploy.sh re-pullea y reinicia).
#
# Flags:
#   --git-pull   git pull antes de pull/up (para refrescar compose o Caddyfile)
#   --logs       sigue logs despues de up

set -eo pipefail

cd "$(dirname "$0")/.."

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"

# --- Checks de prerequisitos ---

if ! command -v docker &>/dev/null; then
    echo "ERROR: docker no esta instalado. Ver DEPLOY.md seccion 2." >&2
    exit 1
fi

if ! docker compose version &>/dev/null; then
    echo "ERROR: 'docker compose' (plugin v2) no esta disponible." >&2
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE no existe. Hace: cp .env.prod.example $ENV_FILE && editarlo" >&2
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "ERROR: $COMPOSE_FILE no existe (correr desde el root del repo)." >&2
    exit 1
fi

# Validar que las envs criticas no esten con placeholder
required_envs=(
    "DOCKERHUB_USER"
    "SUBSCRIPTIONS_DOMAIN"
    "PUBLIC_BASE_URL"
    "SUBSCRIPTIONS_SECRET"
    "SMTP_HOST"
    "SMTP_USER"
    "SMTP_PASS"
    "FROM_ADDR"
)
for var in "${required_envs[@]}"; do
    val=$(grep -E "^${var}=" "$ENV_FILE" | cut -d= -f2- || echo "")
    if [ -z "$val" ] || [[ "$val" == *"__"*"__"* ]] || [[ "$val" == *"xxxxxxxx"* ]] \
        || [[ "$val" == "tu-username" ]] || [[ "$val" == "tu@correo.com" ]]; then
        echo "ERROR: $var en $ENV_FILE esta vacio o con placeholder." >&2
        exit 1
    fi
done

# --- Parse flags ---
GITPULL=0
FOLLOW_LOGS=0
for arg in "$@"; do
    case "$arg" in
        --git-pull) GITPULL=1 ;;
        --logs) FOLLOW_LOGS=1 ;;
        *) echo "WARN: flag desconocida $arg, ignorando" ;;
    esac
done

# --- git pull si se pidio (para actualizar configs/compose/Caddyfile) ---
if [ "$GITPULL" = "1" ]; then
    echo ">> git pull"
    git pull --ff-only
fi

# --- Pull de imagenes desde Docker Hub + up ---
echo ">> docker compose pull (desde Docker Hub)"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull

echo
echo ">> docker compose up"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

# --- Esperar healthchecks ---
echo
echo ">> Esperando que los servicios queden healthy..."
for i in {1..30}; do
    sleep 2
    unhealthy=$(docker compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null \
        | python3 -c "
import json, sys
for line in sys.stdin:
    if not line.strip(): continue
    try:
        d = json.loads(line)
    except json.JSONDecodeError:
        continue
    health = d.get('Health', '')
    if health and health != 'healthy':
        print(d.get('Service', '?'))
" || true)
    if [ -z "$unhealthy" ]; then
        echo "  todos OK"
        break
    fi
    echo "  esperando: $unhealthy (intento $i/30)"
done

# --- Status final ---
echo
echo ">> Status"
docker compose -f "$COMPOSE_FILE" ps

# --- URLs utiles ---
DOMAIN=$(grep -E "^SUBSCRIPTIONS_DOMAIN=" "$ENV_FILE" | cut -d= -f2-)
echo
echo "URLs:"
echo "  Form:     https://${DOMAIN}/"
echo "  Health:   https://${DOMAIN}/health"
echo "  Health (local): curl http://localhost/health"
echo
echo "Disparar digest manual:"
echo "  docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec digest python -c 'from main import run_digest; run_digest()'"

if [ "$FOLLOW_LOGS" = "1" ]; then
    echo
    echo ">> Tailing logs (Ctrl+C para salir)"
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f --tail=20
fi
