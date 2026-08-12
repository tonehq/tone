import json
import os

import pulumi

from components.cache import Cache
from components.db import Db
from components.filestorage import FileStorage
from components.kubernetes import Kubernetes
from components.vm import Vm

HERE = os.path.dirname(os.path.abspath(__file__))
STACK = pulumi.get_stack()

with open(os.path.join(HERE, "environments", f"{STACK}.json")) as fh:
    ENV = json.load(fh)

ENV_NAME = ENV["env_name"]
SERVICES = ENV["services"]

BUILDERS = {
    "kubernetes": Kubernetes,
    "db": Db,
    "cache": Cache,
    "filestorage": FileStorage,
    "vm": Vm,
}

for service_name, builder in BUILDERS.items():
    spec = SERVICES.get(service_name)
    if not spec or not spec.get("provider"):
        continue
    component = builder(service_name, ENV_NAME, spec)
    pulumi.export(service_name, component.outputs)

pulumi.export("env_name", ENV_NAME)
pulumi.export("stack", STACK)
