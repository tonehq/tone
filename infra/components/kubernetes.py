import pulumi
import pulumi_aws as aws
import pulumi_azure_native as azure
import pulumi_digitalocean as digitalocean


class Kubernetes(pulumi.ComponentResource):
    def __init__(self, name, env_name, spec, opts=None):
        super().__init__("tone:service:Kubernetes", name, None, opts)
        self.env_name = env_name
        self.provider_name = spec["provider"]
        cfg = spec["config"]

        dispatch = {
            "aws": self._aws,
            "azure": self._azure,
            "digitalocean": self._digitalocean,
        }
        if self.provider_name not in dispatch:
            raise Exception(
                f"kubernetes provider '{self.provider_name}' is not implemented"
            )
        outputs = dispatch[self.provider_name](cfg)
        outputs["provider"] = self.provider_name
        self.outputs = outputs
        self.register_outputs(outputs)

    def _digitalocean(self, c):
        child = pulumi.ResourceOptions(parent=self)
        env = self.env_name
        pools = c["node_pools"]
        if not pools:
            raise Exception("at least one node pool is required")

        version = c.get("version")
        if not version:
            prefix = c.get("version_prefix") or None
            if prefix:
                found = digitalocean.get_kubernetes_versions(version_prefix=prefix)
                version = found.latest_version
            if not version:
                version = digitalocean.get_kubernetes_versions().latest_version

        default = pools[0]
        cluster = digitalocean.KubernetesCluster(
            f"{env}-doks",
            name=f"{env}-doks",
            region=c["region"],
            version=version,
            auto_upgrade=False,
            node_pool={
                "name": default["name"],
                "size": default["instance_type"],
                "auto_scale": True,
                "min_nodes": default["min"],
                "max_nodes": default["max"],
                "node_count": default["desired"],
                "labels": default.get("labels", {}),
            },
            tags=[env],
            opts=child,
        )

        for pool in pools[1:]:
            digitalocean.KubernetesNodePool(
                f"{env}-{pool['name']}",
                cluster_id=cluster.id,
                name=pool["name"],
                size=pool["instance_type"],
                auto_scale=True,
                min_nodes=pool["min"],
                max_nodes=pool["max"],
                node_count=pool["desired"],
                labels=pool.get("labels", {}),
                tags=[env],
                opts=child,
            )

        return {
            "cluster_name": cluster.name,
            "endpoint": cluster.endpoint,
            "version": cluster.version,
            "region": cluster.region,
            "vpc_id": cluster.vpc_uuid,
            "node_pools": [p["name"] for p in pools],
            "kubeconfig": pulumi.Output.secret(
                cluster.kube_configs.apply(lambda k: k[0].raw_config)
            ),
        }

    def _build_aws_network(self, c, child):
        env = self.env_name
        tags = {"Project": env, "Service": "kubernetes"}

        if c.get("vpc_id"):
            private_ids = c["private_subnet_ids"]
            if not private_ids:
                raise Exception(
                    "private_subnet_ids is required when vpc_id is supplied"
                )
            return {
                "vpc_id": c["vpc_id"],
                "cluster_subnet_ids": c["public_subnet_ids"] + private_ids,
                "node_subnet_ids": [private_ids[0]],
            }

        azs = [c["primary_az"], c["secondary_az"]]
        vpc = aws.ec2.Vpc(
            f"{env}-vpc",
            cidr_block=c["vpc_cidr"],
            enable_dns_hostnames=True,
            enable_dns_support=True,
            tags={**tags, "Name": f"{env}-vpc"},
            opts=child,
        )
        igw = aws.ec2.InternetGateway(
            f"{env}-igw", vpc_id=vpc.id, tags={**tags, "Name": f"{env}-igw"}, opts=child
        )
        use_nat = c.get("nat_gateway", True)

        publics = [
            aws.ec2.Subnet(
                f"{env}-public-{i}",
                vpc_id=vpc.id,
                cidr_block=cidr,
                availability_zone=azs[i % len(azs)],
                map_public_ip_on_launch=not use_nat,
                tags={
                    **tags,
                    "Name": f"{env}-public-{azs[i % len(azs)]}",
                    "kubernetes.io/role/elb": "1",
                    f"kubernetes.io/cluster/{env}": "shared",
                },
                opts=child,
            )
            for i, cidr in enumerate(c["public_subnet_cidrs"])
        ]
        privates = [
            aws.ec2.Subnet(
                f"{env}-private-{i}",
                vpc_id=vpc.id,
                cidr_block=cidr,
                availability_zone=c["primary_az"],
                tags={
                    **tags,
                    "Name": f"{env}-private-{c['primary_az']}",
                    "kubernetes.io/role/internal-elb": "1",
                    f"kubernetes.io/cluster/{env}": "shared",
                },
                opts=child,
            )
            for i, cidr in enumerate(c["private_subnet_cidrs"])
        ]

        public_rt = aws.ec2.RouteTable(
            f"{env}-public-rtb",
            vpc_id=vpc.id,
            tags={**tags, "Name": f"{env}-public-rtb"},
            opts=child,
        )
        aws.ec2.Route(
            f"{env}-public-default",
            route_table_id=public_rt.id,
            destination_cidr_block="0.0.0.0/0",
            gateway_id=igw.id,
            opts=child,
        )
        for i, s in enumerate(publics):
            aws.ec2.RouteTableAssociation(
                f"{env}-public-assoc-{i}",
                route_table_id=public_rt.id,
                subnet_id=s.id,
                opts=child,
            )

        if use_nat:
            eip = aws.ec2.Eip(
                f"{env}-nat-eip",
                domain="vpc",
                tags={**tags, "Name": f"{env}-nat-eip"},
                opts=child,
            )
            nat = aws.ec2.NatGateway(
                f"{env}-nat",
                allocation_id=eip.id,
                subnet_id=publics[0].id,
                tags={**tags, "Name": f"{env}-nat"},
                opts=child,
            )
            private_rt = aws.ec2.RouteTable(
                f"{env}-private-rtb",
                vpc_id=vpc.id,
                tags={**tags, "Name": f"{env}-private-rtb"},
                opts=child,
            )
            aws.ec2.Route(
                f"{env}-private-default",
                route_table_id=private_rt.id,
                destination_cidr_block="0.0.0.0/0",
                nat_gateway_id=nat.id,
                opts=child,
            )
            target_rt, node_subnet = private_rt, privates[0]
        else:
            target_rt, node_subnet = public_rt, publics[0]

        for i, s in enumerate(privates):
            aws.ec2.RouteTableAssociation(
                f"{env}-private-assoc-{i}",
                route_table_id=target_rt.id,
                subnet_id=s.id,
                opts=child,
            )

        return {
            "vpc_id": vpc.id,
            "cluster_subnet_ids": [s.id for s in publics] + [s.id for s in privates],
            "node_subnet_ids": [node_subnet.id],
        }

    def _aws(self, c):
        child = pulumi.ResourceOptions(parent=self)
        env = self.env_name
        tags = {"Project": env, "Service": "kubernetes"}

        net = self._build_aws_network(c, child)

        cluster_role = aws.iam.Role(
            f"{env}-cluster-role",
            name=f"{env}ClusterRole",
            assume_role_policy='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"eks.amazonaws.com"},"Action":"sts:AssumeRole"}]}',
            tags=tags,
            opts=child,
        )
        aws.iam.RolePolicyAttachment(
            f"{env}-cluster-eks-policy",
            role=cluster_role.name,
            policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
            opts=child,
        )
        node_role = aws.iam.Role(
            f"{env}-node-role",
            name=f"{env}NodeRole",
            assume_role_policy='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}',
            tags=tags,
            opts=child,
        )
        for suffix, arn in [
            ("worker", "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"),
            ("cni", "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"),
            ("ecr", "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"),
        ]:
            aws.iam.RolePolicyAttachment(
                f"{env}-node-{suffix}-policy",
                role=node_role.name,
                policy_arn=arn,
                opts=child,
            )

        cluster = aws.eks.Cluster(
            f"{env}-eks",
            name=env,
            role_arn=cluster_role.arn,
            version=c["k8s_version"],
            access_config={
                "authentication_mode": "API_AND_CONFIG_MAP",
                "bootstrap_cluster_creator_admin_permissions": True,
            },
            vpc_config={
                "subnet_ids": net["cluster_subnet_ids"],
                "endpoint_public_access": True,
                "endpoint_private_access": True,
            },
            tags=tags,
            opts=child,
        )

        pool_names = []
        for pool in c["node_pools"]:
            aws.eks.NodeGroup(
                f"{env}-{pool['name']}",
                cluster_name=cluster.name,
                node_group_name=pool["name"],
                node_role_arn=node_role.arn,
                subnet_ids=net["node_subnet_ids"],
                instance_types=[pool["instance_type"]],
                ami_type=pool.get("ami_type", c["ami_type"]),
                capacity_type=pool.get("capacity_type", c["capacity_type"]),
                disk_size=pool.get("disk_size", c["disk_size"]),
                scaling_config={
                    "min_size": pool["min"],
                    "max_size": pool["max"],
                    "desired_size": pool["desired"],
                },
                update_config={"max_unavailable": 1},
                labels=pool.get("labels", {"pool": pool["name"]}),
                taints=pool.get("taints", []),
                tags={**tags, "Name": f"{env}-{pool['name']}"},
                opts=child,
            )
            pool_names.append(pool["name"])

        return {
            "vpc_id": net["vpc_id"],
            "cluster_name": cluster.name,
            "endpoint": cluster.endpoint,
            "version": cluster.version,
            "node_subnets": net["node_subnet_ids"],
            "node_pools": pool_names,
        }

    def _azure(self, c):
        child = pulumi.ResourceOptions(parent=self)
        env = self.env_name
        pools = c["node_pools"]
        if not pools:
            raise Exception("at least one node pool is required")

        rg = azure.resources.ResourceGroup(
            f"{env}-k8s-rg",
            resource_group_name=c["resource_group"],
            location=c["location"],
            tags={"Project": env, "Service": "kubernetes"},
            opts=child,
        )

        system = pools[0]
        system_profile = {
            "name": system["name"],
            "mode": "System",
            "type": "VirtualMachineScaleSets",
            "os_type": "Linux",
            "vm_size": system["instance_type"],
            "os_disk_size_gb": system.get("disk_size", c["os_disk_size_gb"]),
            "count": system["desired"],
            "min_count": system["min"],
            "max_count": system["max"],
            "enable_auto_scaling": True,
        }
        if c.get("availability_zones"):
            system_profile["availability_zones"] = c["availability_zones"]

        cluster = azure.containerservice.ManagedCluster(
            f"{env}-aks",
            resource_group_name=rg.name,
            resource_name_=f"{env}-aks",
            location=c["location"],
            dns_prefix=env,
            kubernetes_version=c["kubernetes_version"],
            identity={"type": "SystemAssigned"},
            agent_pool_profiles=[system_profile],
            tags={"Project": env, "Service": "kubernetes"},
            opts=child,
        )

        for pool in pools[1:]:
            azure.containerservice.AgentPool(
                f"{env}-{pool['name']}",
                resource_group_name=rg.name,
                resource_name_=cluster.name,
                agent_pool_name=pool["name"],
                mode="User",
                type="VirtualMachineScaleSets",
                os_type="Linux",
                vm_size=pool["instance_type"],
                os_disk_size_gb=pool.get("disk_size", c["os_disk_size_gb"]),
                count=pool["desired"],
                min_count=pool["min"],
                max_count=pool["max"],
                enable_auto_scaling=True,
                availability_zones=c.get("availability_zones") or None,
                node_labels=pool.get("labels"),
                node_taints=pool.get("taints"),
                opts=child,
            )

        return {
            "resource_group": rg.name,
            "cluster_name": cluster.name,
            "endpoint": cluster.fqdn,
            "version": cluster.kubernetes_version,
            "node_pools": [p["name"] for p in pools],
        }
