#!/usr/bin/env bash
# Build de las 4 imagenes y push a Docker Hub.
#
# Correr LOCALMENTE (no en la VM). En Mac M1/M2/M3 cross-compila a linux/amd64
# (la VM Oracle E2.1.Micro es AMD64).
#
# Pre-requisitos:
#   1. Cuenta en hub.docker.com
#   2. docker login (te pide username + Personal Access Token, no password)
#   3. DOCKERHUB_USER seteado (env var o en .env.prod)
#
# Uso:
#   ./tools/build_and_push.sh              # build + push de los 4 servicios
#   ./tools/build_and_push.sh subscriptions # solo uno
#   DOCKERHUB_USER=tu-user ./tools/build_and_push.sh

set -eo pipefail

cd "$(dirname "$0")/.."

# --- Resolver DOCKERHUB_USER ---
if [ -z "$DOCKERHUB_USER" ] && [ -f ".env.prod" ]; then
    DOCKERHUB_USER=$(grep -E "^DOCKERHUB_USER=" .env.prod | cut -d= -f2- | tr -d ' "')
fi
if [ -z "$DOCKERHUB_USER" ]; then
    echo "ERROR: DOCKERHUB_USER no esta seteado." >&2
    echo "       export DOCKERHUB_USER=tu-username   o ponelo en .env.prod" >&2
    exit 1
fi

# --- Verificar docker login ---
if ! docker info 2>/dev/null | grep -q "Username:"; then
    echo "WARN: no se detecta sesion de docker login."
    echo "      Correr: docker login -u $DOCKERHUB_USER"
    read -p "Continuar igual? (push fallara si no estas logueado) [y/N] " ans
    [ "$ans" = "y" ] || exit 1
fi

PLATFORM="linux/amd64"
SERVICES=("subscriptions" "digest" "listener" "translator")

# Si pasan args, restringir a esos
if [ "$#" -gt 0 ]; then
    SERVICES=("$@")
fi

for svc in "${SERVICES[@]}"; do
    if [ ! -d "$svc" ]; then
        echo "ERROR: no existe el directorio $svc/" >&2
        exit 1
    fi
    IMAGE="${DOCKERHUB_USER}/arxiv-digest-${svc}:latest"
    echo
    echo "============================================================"
    echo ">> Build $svc -> $IMAGE  (platform: $PLATFORM)"
    echo "============================================================"
    docker build --platform "$PLATFORM" -t "$IMAGE" "./$svc"

    echo
    echo ">> Push $IMAGE"
    docker push "$IMAGE"
done

echo
echo "============================================================"
echo "OK: ${#SERVICES[@]} imagen(es) publicadas en Docker Hub."
echo
echo "URLs:"
for svc in "${SERVICES[@]}"; do
    echo "  https://hub.docker.com/r/${DOCKERHUB_USER}/arxiv-digest-${svc}"
done
echo
echo "Para deployar en la VM:"
echo "  ssh ubuntu@<IP>"
echo "  cd ~/arxiv-digest"
echo "  ./tools/deploy.sh"
