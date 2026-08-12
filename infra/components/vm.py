import os

import pulumi
import pulumi_digitalocean as digitalocean


class Vm(pulumi.ComponentResource):
    def __init__(self, name, env_name, spec, opts=None):
        super().__init__("tone:service:Vm", name, None, opts)
        self.env_name = env_name
        self.provider_name = spec["provider"]
        cfg = spec["config"]

        dispatch = {"digitalocean": self._digitalocean}
        if self.provider_name not in dispatch:
            raise Exception(f"vm provider '{self.provider_name}' is not implemented")
        outputs = dispatch[self.provider_name](cfg)
        outputs["provider"] = self.provider_name
        self.outputs = outputs
        self.register_outputs(outputs)

    def _digitalocean(self, c):
        child = pulumi.ResourceOptions(parent=self)
        env = self.env_name

        ssh_keys = []
        for key_name in c.get("ssh_key_names", []):
            ssh_keys.append(digitalocean.get_ssh_key(name=key_name).id)

        for i, path in enumerate(c.get("ssh_public_key_paths", [])):
            with open(os.path.expanduser(path)) as fh:
                material = fh.read().strip()
            key = digitalocean.SshKey(
                f"{env}-key-{i}",
                name=f"{env}-key-{i}",
                public_key=material,
                opts=child,
            )
            ssh_keys.append(key.id)

        if not ssh_keys:
            raise Exception(
                "no ssh keys: set ssh_key_names or ssh_public_key_paths, "
                "otherwise the droplet is unreachable"
            )

        droplet = digitalocean.Droplet(
            f"{env}-vm",
            name=f"{env}-vm",
            region=c["region"],
            size=c["size"],
            image=c["image"],
            ssh_keys=ssh_keys,
            monitoring=c.get("monitoring", True),
            backups=c.get("backups", False),
            user_data=c.get("user_data") or None,
            tags=[env],
            opts=child,
        )

        firewall = digitalocean.Firewall(
            f"{env}-vm-fw",
            name=f"{env}-vm-fw",
            droplet_ids=[droplet.id],
            inbound_rules=[
                {
                    "protocol": "tcp",
                    "port_range": str(port),
                    "source_addresses": c.get("allowed_sources", ["0.0.0.0/0", "::/0"]),
                }
                for port in c["open_ports"]
            ],
            outbound_rules=[
                {
                    "protocol": "tcp",
                    "port_range": "1-65535",
                    "destination_addresses": ["0.0.0.0/0", "::/0"],
                },
                {
                    "protocol": "udp",
                    "port_range": "1-65535",
                    "destination_addresses": ["0.0.0.0/0", "::/0"],
                },
                {
                    "protocol": "icmp",
                    "destination_addresses": ["0.0.0.0/0", "::/0"],
                },
            ],
            opts=child,
        )

        result = {
            "droplet_id": droplet.id,
            "name": droplet.name,
            "public_ip": droplet.ipv4_address,
            "private_ip": droplet.ipv4_address_private,
            "region": droplet.region,
            "size": droplet.size,
            "image": c["image"],
            "firewall_id": firewall.id,
            "open_ports": c["open_ports"],
        }

        if c.get("reserved_ip"):
            reserved = digitalocean.ReservedIp(
                f"{env}-vm-ip",
                region=c["region"],
                droplet_id=droplet.id.apply(lambda i: int(i)),
                opts=child,
            )
            result["reserved_ip"] = reserved.ip_address

        return result
