"""DigitalOcean DOKS app node pool — a secondary KubernetesNodePool on an existing cluster.

Mirrors the KubernetesNodePool pattern in infra/components/kubernetes.py:_digitalocean.
"""

import pulumi
import pulumi_digitalocean as digitalocean

from .base import AppNodePool


class DoNodePool(AppNodePool):
    def create(self, opts):
        c = self.cfg
        cluster = digitalocean.get_kubernetes_cluster(name=c["clusterName"])
        autoscale = bool(c.get("autoScale", False))
        if autoscale:
            # The autoscaler owns the live node count — don't let `pulumi up` reset it.
            # `node_count` is translated to the provider's `nodeCount` by the Python SDK.
            opts = pulumi.ResourceOptions.merge(
                opts, pulumi.ResourceOptions(ignore_changes=["node_count"])
            )
        return digitalocean.KubernetesNodePool(
            "app-user-pool",
            cluster_id=cluster.id,
            name=self.name,
            size=c["size"],
            auto_scale=autoscale,
            node_count=c.get("nodeCount", 1),
            min_nodes=c.get("minNodes") if autoscale else None,
            max_nodes=c.get("maxNodes") if autoscale else None,
            labels=c.get("labels") or None,
            tags=c.get("tags") or None,
            opts=opts,
        )
