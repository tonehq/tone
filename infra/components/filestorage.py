import pulumi
import pulumi_cloudflare as cloudflare


class FileStorage(pulumi.ComponentResource):
    def __init__(self, name, env_name, spec, opts=None):
        super().__init__("tone:service:FileStorage", name, None, opts)
        self.env_name = env_name
        self.provider_name = spec["provider"]
        cfg = spec["config"]

        dispatch = {"cloudflare": self._cloudflare}
        if self.provider_name not in dispatch:
            raise Exception(
                f"filestorage provider '{self.provider_name}' is not implemented"
            )
        outputs = dispatch[self.provider_name](cfg)
        outputs["provider"] = self.provider_name
        self.outputs = outputs
        self.register_outputs(outputs)

    def _cloudflare(self, c):
        child = pulumi.ResourceOptions(parent=self)
        env = self.env_name

        bucket = cloudflare.R2Bucket(
            f"{env}-bucket",
            account_id=c["account_id"],
            name=c["bucket_name"],
            location=c["location"],
            storage_class=c["storage_class"],
            opts=child,
        )

        return {
            "bucket_name": bucket.name,
            "bucket_id": bucket.id,
            "location": bucket.location,
        }
