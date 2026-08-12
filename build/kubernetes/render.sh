#!/usr/bin/env bash
#
# Render a manifest template set for one environment.
#
#   ./build/kubernetes/render.sh <env-file> [out-dir] [template-dir]
#
# Examples:
#   # App manifests (default template dir = _base)
#   ./build/kubernetes/render.sh build/kubernetes/envs/staging-do.env
#     -> build/kubernetes/.rendered/staging-do/
#
#   # Monitoring manifests (separate, per-cluster unit)
#   ./build/kubernetes/render.sh build/kubernetes/envs/staging-do.env \
#       build/kubernetes/.rendered/staging-do-monitoring \
#       build/kubernetes/monitoring
#
# Every ${VAR} placeholder in the templates is substituted from the env file.
# Two tokens are deliberately LEFT untouched for downstream steps:
#   ${IMAGE_TAG}  -> substituted by CI (the built image sha)
#   $(POD_NAME)   -> a Kubernetes downward-API fieldRef, not a template var
#
set -euo pipefail

ENV_FILE="${1:?usage: render.sh <env-file> [out-dir] [template-dir]}"
NAME="$(basename "$ENV_FILE" .env)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${2:-$SCRIPT_DIR/.rendered/$NAME}"
BASE="${3:-$SCRIPT_DIR/_base}"

# Load env vars
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# Required for every render
: "${NAMESPACE:?}" "${RESOURCE_PREFIX:?}" "${ENVIRONMENT:?}" "${APP_ENV:?}"
: "${API_DOMAIN:?}" "${CALL_DOMAIN:?}" "${IMAGE_REPO:?}" "${INFISICAL_HOST:?}"
# Capacity / behaviour
: "${API_REPLICAS:?}" "${CALL_REPLICAS:?}" "${OUTBOUND_REPLICAS:?}"
: "${INBOUND_MAX_CONCURRENT_CALLS:?}" "${OUTBOUND_MAX_CONCURRENT_CALLS:?}"
: "${API_CPU_REQUEST:?}" "${API_MEM_REQUEST:?}" "${API_CPU_LIMIT:?}" "${API_MEM_LIMIT:?}"
: "${CALL_CPU_REQUEST:?}" "${CALL_MEM_REQUEST:?}" "${CALL_CPU_LIMIT:?}" "${CALL_MEM_LIMIT:?}"
: "${OUTBOUND_CPU_REQUEST:?}" "${OUTBOUND_MEM_REQUEST:?}" "${OUTBOUND_CPU_LIMIT:?}" "${OUTBOUND_MEM_LIMIT:?}"
: "${DOCWORKER_CPU_REQUEST:?}" "${DOCWORKER_MEM_REQUEST:?}" "${DOCWORKER_CPU_LIMIT:?}" "${DOCWORKER_MEM_LIMIT:?}"
: "${ORCH_CPU_REQUEST:?}" "${ORCH_MEM_REQUEST:?}" "${ORCH_CPU_LIMIT:?}" "${ORCH_MEM_LIMIT:?}"
: "${DOC_MIN_REPLICAS:?}" "${DOC_MAX_REPLICAS:?}" "${OUTBOUND_MIN_REPLICAS:?}" "${OUTBOUND_MAX_REPLICAS:?}"
: "${LETSENCRYPT_EMAIL:?}"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

# One sed -e per template variable. Order-independent (each token is unique).
subst=(
  NAMESPACE RESOURCE_PREFIX ENVIRONMENT APP_ENV API_DOMAIN CALL_DOMAIN
  IMAGE_REPO INFISICAL_HOST LETSENCRYPT_EMAIL
  API_REPLICAS CALL_REPLICAS OUTBOUND_REPLICAS
  INBOUND_MAX_CONCURRENT_CALLS OUTBOUND_MAX_CONCURRENT_CALLS
  API_CPU_REQUEST API_MEM_REQUEST API_CPU_LIMIT API_MEM_LIMIT
  CALL_CPU_REQUEST CALL_MEM_REQUEST CALL_CPU_LIMIT CALL_MEM_LIMIT
  OUTBOUND_CPU_REQUEST OUTBOUND_MEM_REQUEST OUTBOUND_CPU_LIMIT OUTBOUND_MEM_LIMIT
  DOCWORKER_CPU_REQUEST DOCWORKER_MEM_REQUEST DOCWORKER_CPU_LIMIT DOCWORKER_MEM_LIMIT
  ORCH_CPU_REQUEST ORCH_MEM_REQUEST ORCH_CPU_LIMIT ORCH_MEM_LIMIT
  DOC_MIN_REPLICAS DOC_MAX_REPLICAS OUTBOUND_MIN_REPLICAS OUTBOUND_MAX_REPLICAS
)
sed_args=()
for v in "${subst[@]}"; do
  sed_args+=(-e "s|\${$v}|${!v}|g")
done

while IFS= read -r -d '' f; do
  rel="${f#"$BASE"/}"
  mkdir -p "$OUT_DIR/$(dirname "$rel")"
  sed "${sed_args[@]}" "$f" > "$OUT_DIR/$rel"
done < <(find "$BASE" -type f -name '*.yaml' -print0)

echo "Rendered $ENV_FILE ($BASE) -> $OUT_DIR"
