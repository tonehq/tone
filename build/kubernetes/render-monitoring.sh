#!/usr/bin/env bash
#
# Render the shared monitoring/ templates for ONE cluster.
# Monitoring is per-cluster and env-agnostic — its only variable is CLUSTER_NAME,
# so this renderer needs no app env file.
#
#   ./build/kubernetes/render-monitoring.sh <cluster-name> [out-dir]
#
# Example:
#   ./build/kubernetes/render-monitoring.sh tonedo-doks
#     -> build/kubernetes/.rendered/monitoring-tonedo-doks/
#
set -euo pipefail

CLUSTER_NAME="${1:?usage: render-monitoring.sh <cluster-name> [out-dir]}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/monitoring"
OUT_DIR="${2:-$SCRIPT_DIR/.rendered/monitoring-$CLUSTER_NAME}"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

for f in "$SRC"/*.yaml; do
  sed "s|\${CLUSTER_NAME}|${CLUSTER_NAME}|g" "$f" > "$OUT_DIR/$(basename "$f")"
done

echo "Rendered monitoring (cluster=$CLUSTER_NAME) -> $OUT_DIR"
