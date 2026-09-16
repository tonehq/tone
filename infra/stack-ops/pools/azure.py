"""Azure AKS app node pool (User or System mode) on an existing cluster.

mode="User" for the classic 2-pool model; "System" when this is the cluster's only pool. Mirrors the
AgentPool pattern in infra/components/kubernetes.py:_azure.
"""

import pulumi
import pulumi_azure_native as azure

from .base import AppNodePool


class AzureAgentPool(AppNodePool):
    def create(self, opts):
        c = self.cfg
        autoscale = bool(c.get("enableAutoScaling", False))
        if autoscale:
            # The autoscaler owns the live node count — don't let `pulumi up` reset it.
            opts = pulumi.ResourceOptions.merge(
                opts, pulumi.ResourceOptions(ignore_changes=["count"])
            )
        # Azure requires the initial count >= minCount when autoscaling; fall back to
        # minCount rather than a fixed 1 so an omitted `count` doesn't fail at apply time.
        count = c.get("count")
        if count is None:
            count = c.get("minCount", 1) if autoscale else 1
        return azure.containerservice.AgentPool(
            "app-user-pool",
            resource_group_name=c["resourceGroup"],
            resource_name_=c["clusterName"],
            agent_pool_name=self.name,
            mode=c.get("mode", "User"),
            type="VirtualMachineScaleSets",
            os_type="Linux",
            vm_size=c["vmSize"],
            os_disk_size_gb=c.get("osDiskSizeGb", 128),
            count=count,
            min_count=c.get("minCount") if autoscale else None,
            max_count=c.get("maxCount") if autoscale else None,
            enable_auto_scaling=autoscale,
            availability_zones=c.get("availabilityZones") or None,
            node_labels=c.get("labels") or None,
            node_taints=c.get("taints") or None,
            opts=opts,
        )
