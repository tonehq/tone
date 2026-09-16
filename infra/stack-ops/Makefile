# tone — start/stop for the Tone app stack (DigitalOcean + Azure). See README.md.
# Stacks: staging (DO) · staging-azure (Azure)   [also: do · azure]
#
# DigitalOcean stop/start = destroy/recreate the disposable app node pool (droplets off = cost off):
#   make do-start   [STACK=staging]        pulumi up      -> create the app pool
#   make do-stop    [STACK=staging]        pulumi destroy -> delete the app pool
# Azure stop/start = pause/resume the whole cluster (all nodes deallocated):
#   make az-start   [RG=.. CLUSTER=..]     az aks start
#   make az-stop    [RG=.. CLUSTER=..]     az aks stop
# App-only (either cloud, cluster stays up) = scale the Deployments 0<->REPLICAS:
#   make app-start / app-stop              (run `make kubeconfig-do` or `-azure` first)
# Provision/maintain the app pool with Pulumi:
#   make pool-apply / pool-preview [STACK=..]
#   make status [STACK=..]

STACK       ?= staging
PULUMI      ?= pulumi
NS          ?= default
DEPLOYMENTS ?= tone-api tone-call-worker
REPLICAS    ?= 1

# Azure cluster identity (for az-start/az-stop + kubeconfig-azure); override per Azure stack.
RG          ?= tone-staging
CLUSTER     ?= tone-staging-aks
# DigitalOcean cluster name (for kubeconfig-do); override per DO stack.
DO_CLUSTER  ?= tone-staging-doks

.PHONY: do-start do-stop az-start az-stop app-start app-stop pool-apply pool-preview \
        kubeconfig-do kubeconfig-azure status

# --- DigitalOcean: destroy/recreate the app pool (droplets off = node cost off) ---
do-start:
	$(PULUMI) up --stack $(STACK) --yes

do-stop:
	$(PULUMI) destroy --stack $(STACK) --yes

# --- Azure: whole-cluster power off/on ---
az-start:
	az aks start --resource-group $(RG) --name $(CLUSTER)

az-stop:
	az aks stop --resource-group $(RG) --name $(CLUSTER)

# --- Provision / maintain the app node pool (either cloud) ---
pool-apply:
	$(PULUMI) up --stack $(STACK) --yes

pool-preview:
	$(PULUMI) preview --stack $(STACK)

# --- App-only scale (cluster stays up). Fetch a kubeconfig first (targets below). ---
app-start:
	kubectl -n $(NS) scale deployment $(DEPLOYMENTS) --replicas=$(REPLICAS)

app-stop:
	kubectl -n $(NS) scale deployment $(DEPLOYMENTS) --replicas=0

kubeconfig-do:
	doctl kubernetes cluster kubeconfig save $(DO_CLUSTER)

kubeconfig-azure:
	az aks get-credentials --resource-group $(RG) --name $(CLUSTER) --admin --overwrite-existing

status:
	@echo "== pulumi stack ($(STACK)) =="
	-@$(PULUMI) stack output --stack $(STACK) 2>/dev/null || echo "(no outputs — app pool is down)"
	@printf '\n== workloads (ns=$(NS)) ==\n'
	-@kubectl -n $(NS) get deploy,pods -o wide 2>/dev/null || echo "(run make kubeconfig-do | kubeconfig-azure first)"
