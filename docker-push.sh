#!/usr/bin/env bash
set -euo pipefail

REGISTRY="${REGISTRY:-}"
BACKEND_IMAGE="${BACKEND_IMAGE:-stock-calculator-backend}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-stock-calculator-frontend}"
REMOTE_HOST="${REMOTE_HOST:-root@123.56.122.63}"
REMOTE_PATH="${REMOTE_PATH:-/usr/vic/stock-images}"
OUTPUT_DIR="${OUTPUT_DIR:-./dist-images}"
BACKEND_VERSION="${BACKEND_VERSION:-$(node scripts/read-version.mjs backend)}"
FRONTEND_VERSION="${FRONTEND_VERSION:-$(node scripts/read-version.mjs frontend)}"

if [[ -n "${IMAGE_TAG:-}" ]]; then
  BACKEND_VERSION="${IMAGE_TAG}"
  FRONTEND_VERSION="${IMAGE_TAG}"
fi

image_ref() {
  local image="$1"
  local version="$2"
  if [[ -n "${REGISTRY}" ]]; then
    printf "%s/%s:%s" "${REGISTRY}" "${image}" "${version}"
  else
    printf "%s:%s" "${image}" "${version}"
  fi
}

BACKEND_REF="$(image_ref "${BACKEND_IMAGE}" "${BACKEND_VERSION}")"
FRONTEND_REF="$(image_ref "${FRONTEND_IMAGE}" "${FRONTEND_VERSION}")"
BACKEND_TAR="${OUTPUT_DIR}/backend-${BACKEND_VERSION}.tar"
FRONTEND_TAR="${OUTPUT_DIR}/frontend-${FRONTEND_VERSION}.tar"

mkdir -p "${OUTPUT_DIR}"

docker image inspect "${BACKEND_REF}" >/dev/null
docker image inspect "${FRONTEND_REF}" >/dev/null

echo "Saving backend image: ${BACKEND_REF} -> ${BACKEND_TAR}"
docker save -o "${BACKEND_TAR}" "${BACKEND_REF}"

echo "Saving frontend image: ${FRONTEND_REF} -> ${FRONTEND_TAR}"
docker save -o "${FRONTEND_TAR}" "${FRONTEND_REF}"

echo "Creating remote directory: ${REMOTE_HOST}:${REMOTE_PATH}"
ssh "${REMOTE_HOST}" "mkdir -p '${REMOTE_PATH}'"

echo "Uploading image archives..."
scp \
  "${BACKEND_TAR}" \
  "${FRONTEND_TAR}" \
  docker-compose.prod.yml \
  "${REMOTE_HOST}:${REMOTE_PATH}/"

echo "Done."
echo "On the server, load them with:"
echo "  docker load -i ${REMOTE_PATH}/$(basename "${BACKEND_TAR}")"
echo "  docker load -i ${REMOTE_PATH}/$(basename "${FRONTEND_TAR}")"
echo "  cd ${REMOTE_PATH}"
echo "  docker compose -f docker-compose.prod.yml up -d"
