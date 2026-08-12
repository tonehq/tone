import pulumi
import pulumi_azure_native as azure
import pulumi_digitalocean as digitalocean
import pulumi_neon as neon
import pulumi_random as random


class Db(pulumi.ComponentResource):
    def __init__(self, name, env_name, spec, opts=None):
        super().__init__("tone:service:Db", name, None, opts)
        self.env_name = env_name
        self.provider_name = spec["provider"]
        cfg = spec["config"]

        dispatch = {
            "neon": self._neon,
            "azure": self._azure,
            "digitalocean": self._digitalocean,
        }
        if self.provider_name not in dispatch:
            raise Exception(f"db provider '{self.provider_name}' is not implemented")
        outputs = dispatch[self.provider_name](cfg)
        outputs["provider"] = self.provider_name
        self.outputs = outputs
        self.register_outputs(outputs)

    def _neon(self, c):
        child = pulumi.ResourceOptions(parent=self)
        env = self.env_name

        project = neon.Project(
            f"{env}-db",
            name=f"{env}-db",
            org_id=c["org_id"],
            region_id=c["region_id"],
            pg_version=c["pg_version"],
            branch=neon.ProjectBranchArgs(
                name=c["branch_name"],
                database_name=c["database_name"],
                role_name=c["role_name"],
            ),
            opts=child,
        )

        return {
            "project_id": project.id,
            "host": project.database_host,
            "database": project.database_name,
            "user": project.database_user,
            "branch_id": project.default_branch_id,
            "endpoint_id": project.default_endpoint_id,
            "password": pulumi.Output.secret(project.database_password),
            "connection_uri": pulumi.Output.secret(project.connection_uri),
            "connection_uri_pooler": pulumi.Output.secret(project.connection_uri_pooler),
        }

    def _digitalocean(self, c):
        child = pulumi.ResourceOptions(parent=self)
        env = self.env_name

        cluster = digitalocean.DatabaseCluster(
            f"{env}-pg",
            name=f"{env}-pg",
            engine="pg",
            version=c["version"],
            size=c["size"],
            region=c["region"],
            node_count=c["node_count"],
            tags=[env],
            opts=child,
        )

        database = digitalocean.DatabaseDb(
            f"{env}-pg-db",
            cluster_id=cluster.id,
            name=c["database_name"],
            opts=child,
        )

        return {
            "cluster_id": cluster.id,
            "host": cluster.host,
            "private_host": cluster.private_host,
            "port": cluster.port,
            "database": database.name,
            "user": cluster.user,
            "version": cluster.version,
            "region": cluster.region,
            "password": pulumi.Output.secret(cluster.password),
            "connection_uri": pulumi.Output.secret(cluster.uri),
            "connection_uri_private": pulumi.Output.secret(cluster.private_uri),
        }

    def _azure(self, c):
        child = pulumi.ResourceOptions(parent=self)
        env = self.env_name

        rg = azure.resources.ResourceGroup(
            f"{env}-db-rg",
            resource_group_name=c["resource_group"],
            location=c["location"],
            tags={"Project": env, "Service": "db"},
            opts=child,
        )

        password = random.RandomPassword(
            f"{env}-db-password",
            length=24,
            special=True,
            override_special="!#$%*-_",
            opts=child,
        )

        server = azure.dbforpostgresql.Server(
            f"{env}-pg",
            resource_group_name=rg.name,
            server_name=c["server_name"],
            location=c["location"],
            version=c["version"],
            administrator_login=c["administrator_login"],
            administrator_login_password=password.result,
            sku={"name": c["sku_name"], "tier": c["sku_tier"]},
            storage={"storage_size_gb": c["storage_gb"]},
            backup={"backup_retention_days": 7, "geo_redundant_backup": "Disabled"},
            high_availability={"mode": "Disabled"},
            tags={"Project": env, "Service": "db"},
            opts=child,
        )

        return {
            "resource_group": rg.name,
            "server_name": server.name,
            "host": server.fully_qualified_domain_name,
            "version": server.version,
            "user": c["administrator_login"],
            "password": pulumi.Output.secret(password.result),
        }
