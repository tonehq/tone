"""tone — Pulumi IaC for the Tone app node pool.

Provisions a disposable app node pool on an EXISTING cluster (it does not create the cluster/DB/cache).
Start/stop of the running stack is operational — see the Makefile: on DigitalOcean `pulumi up`/`destroy`
creates/removes the app node pool droplets. This program only keeps the node pool defined as code; the
always-on baseline (DOKS control plane, DO Postgres, DO Valkey) lives in the sibling infra/ program.
"""

import pulumi

from pools import create_app_pool

config = pulumi.Config()

PROVIDER = config.require("provider")            # "digitalocean" | "azure"
NAMESPACE = config.get("namespace") or "default"

pool_cfg = dict(config.require_object("appPool"))
pool_cfg["clusterName"] = config.require("clusterName")
if PROVIDER == "azure":
    pool_cfg["resourceGroup"] = config.require("resourceGroup")

create_app_pool(PROVIDER, pool_cfg["name"], pool_cfg, pulumi.ResourceOptions())

pulumi.export("kubernetes_provider", PROVIDER)
pulumi.export("cluster_name", pool_cfg["clusterName"])
pulumi.export("namespace", NAMESPACE)
pulumi.export("app_pool_name", pool_cfg["name"])
