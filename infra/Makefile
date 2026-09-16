# infra/Makefile — operate the Tone Pulumi stacks.
#
#   make <target> [STACK=do]     STACK defaults to the DigitalOcean stack.
#   make up STACK=dev            act on a different stack.
#   make up CI=1                 non-interactive (for pipelines).
#
# Valid stacks: do | dev | infisical | demo  (see environments/*.json).

STACK  ?= do
PULUMI ?= pulumi

# Non-interactive flags, added only when CI=1 so up/down auto-confirm.
ifeq ($(CI),1)
  YES := --yes --non-interactive
endif

.DEFAULT_GOAL := help
.PHONY: help bootstrap select preview up down destroy refresh outputs config whoami

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  STACK=$(STACK)  (override: make up STACK=dev)"

bootstrap: ## Create venv + install deps (incl. vendored SDKs) and plugins
	$(PULUMI) install

select: ## Select STACK, creating it from its Pulumi.<stack>.yaml if missing
	@$(PULUMI) stack select $(STACK) 2>/dev/null || $(PULUMI) stack init $(STACK)

preview: select ## Dry-run: show what `up` would change (read-only)
	$(PULUMI) preview

up: select ## Bring the stack UP (create/update resources)
	$(PULUMI) up $(YES)

down destroy: select ## Tear the stack DOWN (destroy all resources)
	$(PULUMI) destroy $(YES)

refresh: select ## Reconcile state with real cloud resources (drift check)
	$(PULUMI) refresh $(YES)

outputs: select ## Show stack outputs (add --show-secrets manually for secrets)
	$(PULUMI) stack output

config: select ## Show stack config
	$(PULUMI) config

whoami: ## Show the active Pulumi backend / user
	$(PULUMI) whoami -v
