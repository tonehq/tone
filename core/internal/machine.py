import hashlib
import platform
import uuid

from loguru import logger


def get_machine_id() -> str:
    try:
        if platform.system() == "Linux":
            try:
                with open("/etc/machine-id", "r") as f:
                    return f.read().strip()
            except Exception:
                logger.debug("Failed to read /etc/machine-id; trying dbus machine-id")
            try:
                with open("/var/lib/dbus/machine-id", "r") as f:
                    return f.read().strip()
            except Exception:
                logger.debug("Failed to read /var/lib/dbus/machine-id; falling back")

        elif platform.system() == "Darwin":
            try:
                import subprocess
                result = subprocess.run(
                    ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.split("\n"):
                    if "IOPlatformUUID" in line:
                        return line.split('"')[-2]
            except Exception:
                logger.debug("Failed to read IOPlatformUUID; falling back")

        elif platform.system() == "Windows":
            try:
                import subprocess
                result = subprocess.run(
                    ["wmic", "csproduct", "get", "UUID"],
                    capture_output=True,
                    text=True
                )
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    return lines[1].strip()
            except Exception:
                logger.debug("Failed to read Windows csproduct UUID; falling back")

        return str(uuid.getnode())

    except Exception:
        logger.exception("Failed to determine machine id; falling back to uuid.getnode()")
        return str(uuid.getnode())


def get_database_id(db_url: str) -> str:
    return hashlib.sha256(db_url.encode()).hexdigest()[:32]


def generate_fingerprint(db_url: str) -> str:
    machine_id = get_machine_id()
    db_id = get_database_id(db_url)
    combined = f"{machine_id}:{db_id}"
    return hashlib.sha256(combined.encode()).hexdigest()
