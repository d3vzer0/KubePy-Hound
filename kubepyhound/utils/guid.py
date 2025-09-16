import uuid


def get_guid(
    cluster: str, scope: str, kube_type: str, name: str, namespace=uuid.NAMESPACE_DNS
) -> str:
    name = f"kubecluster/{cluster}/{scope}/{kube_type}/{name}"
    return str(uuid.uuid5(namespace, name))
