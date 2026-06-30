#!/usr/bin/env bash
set -euo pipefail

REGISTRY="${REGISTRY:-}"
BASE_REGISTRY="${BASE_REGISTRY:-docker.io}"
PLATFORM="${PLATFORM:-linux/amd64}"
BACKEND_IMAGE="${BACKEND_IMAGE:-stock-calculator-backend}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-stock-calculator-frontend}"
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

echo "Building backend image: ${BACKEND_REF}"
docker build \
  --platform "${PLATFORM}" \
  --build-arg "BASE_REGISTRY=${BASE_REGISTRY}" \
  -t "${BACKEND_REF}" \
  ./backend

echo "Building frontend image: ${FRONTEND_REF}"
docker build \
  --platform "${PLATFORM}" \
  --build-arg "BASE_REGISTRY=${BASE_REGISTRY}" \
  -t "${FRONTEND_REF}" \
  ./frontend

echo "Done."
echo "Backend:  ${BACKEND_REF}"
echo "Frontend: ${FRONTEND_REF}"
