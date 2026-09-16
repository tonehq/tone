#!/usr/bin/env bash
# tone stack-ops — one-shot: store config (secrets included) + provision the app pool.
#
# Prereq: `pulumi login` to the target account first (pulumi whoami -v to confirm).
#         For Azure, the AKS cluster must already exist (provisioned by the sibling infra/ project).
#
# Usage — fill values as env vars, then run:
#   SUBSCRIPTION_ID=<guid> AKS_RG=<resource-group> AKS_CLUSTER=<cluster> ./setup.sh azure
#   DO_TOKEN=<do-token> ./setup.sh do
#
# Secrets (subscriptionId / DO token) are written with `pulumi config set --secret`,
# so they land encrypted in Pulumi.<stack>.yaml — never in plaintext.
set -euo pipefail

STACK="${1:-azure}"
cd "$(dirname "$0")"

# venv + deps
[ -d venv ] || { python3 -m venv venv && ./venv/bin/pip install -r requirements.txt; }

# create or select the stack on the logged-in account
pulumi stack select "$STACK" 2>/dev/null || pulumi stack init "$STACK"

case "$STACK" in
  azure)
    : "${SUBSCRIPTION_ID:?set SUBSCRIPTION_ID=<azure-subscription-guid>}"
    : "${AKS_RG:?set AKS_RG=<aks-resource-group>}"
    : "${AKS_CLUSTER:?set AKS_CLUSTER=<aks-cluster-name>}"
    pulumi config set --secret azure-native:subscriptionId "$SUBSCRIPTION_ID" --stack "$STACK"
    pulumi config set tone:resourceGroup "$AKS_RG"      --stack "$STACK"
    pulumi config set tone:clusterName   "$AKS_CLUSTER" --stack "$STACK"
    ;;
  do)
    : "${DO_TOKEN:?set DO_TOKEN=<digitalocean-api-token>}"
    pulumi config set --secret digitalocean:token "$DO_TOKEN" --stack "$STACK"
    [ -n "${DO_CLUSTER:-}" ] && pulumi config set tone:clusterName "$DO_CLUSTER" --stack "$STACK"
    ;;
  *)
    echo "unknown stack '$STACK' (expected azure | do)"; exit 1 ;;
esac

echo ">> config:"; pulumi config --stack "$STACK"
echo ">> provisioning the app node pool..."
pulumi up --stack "$STACK"
