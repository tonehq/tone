import pulumi
import pulumi_azure_native as azure
import pulumi_digitalocean as digitalocean
import pulumi_upstash as upstash


class Cache(pulumi.ComponentResource):
    def __init__(self, name, env_name, spec, opts=None):
        super().__init__("tone:service:Cache", name, None, opts)
        self.env_name = env_name
        self.provider_name = spec["provider"]
        cfg = spec["config"]

        dispatch = {
            "upstash": self._upstash,
            "azure": self._azure,
            "digitalocean": self._digitalocean,
        }
        if self.provider_name not in dispatch:
            raise Exception(f"cache provider '{self.provider_name}' is not implemented")
        outputs = dispatch[self.provider_name](cfg)
        outputs["provider"] = self.provider_name
        self.outputs = outputs
        self.register_outputs(outputs)

    def _upstash(self, c):
        child = pulumi.ResourceOptions(parent=self)
        env = self.env_name

        database = upstash.RedisDatabase(
            f"{env}-redis",
            database_name=f"{env}-redis",
            region=c["region"],
            primary_region=c["primary_region"],
            eviction=c["eviction"],
            tls=c["tls"],
            opts=child,
        )

        url = pulumi.Output.all(
            database.endpoint, database.port, database.password
        ).apply(lambda a: f"rediss://default:{a[2]}@{a[0]}:{a[1]}")

        return {
            "database_id": database.database_id,
            "name": database.database_name,
            "endpoint": database.endpoint,
            "port": database.port,
            "region": database.region,
            "primary_region": database.primary_region,
            "state": database.state,
            "password": pulumi.Output.secret(database.password),
            "rest_token": pulumi.Output.secret(database.rest_token),
            "url": pulumi.Output.secret(url),
        }

    def _digitalocean(self, c):
        child = pulumi.ResourceOptions(parent=self)
        env = self.env_name

        cluster = digitalocean.DatabaseCluster(
            f"{env}-redis",
            name=f"{env}-redis",
            engine=c["engine"],
            version=c["version"],
            size=c["size"],
            region=c["region"],
            node_count=c["node_count"],
            eviction_policy=c.get("eviction_policy"),
            tags=[env],
            opts=child,
        )

        return {
            "cluster_id": cluster.id,
            "name": cluster.name,
            "endpoint": cluster.host,
            "private_endpoint": cluster.private_host,
            "port": cluster.port,
            "region": cluster.region,
            "user": cluster.user,
            "password": pulumi.Output.secret(cluster.password),
            "url": pulumi.Output.secret(cluster.uri),
            "url_private": pulumi.Output.secret(cluster.private_uri),
        }

    def _azure(self, c):
        child = pulumi.ResourceOptions(parent=self)
        env = self.env_name

        rg = azure.resources.ResourceGroup(
            f"{env}-cache-rg",
            resource_group_name=c["resource_group"],
            location=c["location"],
            tags={"Project": env, "Service": "cache"},
            opts=child,
        )

        cluster = azure.redisenterprise.RedisEnterprise(
            f"{env}-redis",
            resource_group_name=rg.name,
            cluster_name=c["cache_name"],
            location=c["location"],
            sku={"name": c["sku_name"]},
            public_network_access="Enabled",
            minimum_tls_version="1.2",
            tags={"Project": env, "Service": "cache"},
            opts=child,
        )

        database = azure.redisenterprise.Database(
            f"{env}-redis-db",
            resource_group_name=rg.name,
            cluster_name=cluster.name,
            database_name="default",
            client_protocol="Encrypted",
            port=10000,
            eviction_policy=c["eviction_policy"],
            clustering_policy="EnterpriseCluster",
            access_keys_authentication="Enabled",
            opts=child,
        )

        keys = pulumi.Output.all(rg.name, cluster.name, database.name).apply(
            lambda a: azure.redisenterprise.list_database_keys_output(
                resource_group_name=a[0], cluster_name=a[1], database_name=a[2]
            )
        )
        url = pulumi.Output.all(cluster.host_name, database.port, keys).apply(
            lambda a: f"rediss://:{a[2].primary_key}@{a[0]}:{a[1]}"
        )

        return {
            "resource_group": rg.name,
            "name": cluster.name,
            "endpoint": cluster.host_name,
            "port": database.port,
            "sku": c["sku_name"],
            "url": pulumi.Output.secret(url),
        }
