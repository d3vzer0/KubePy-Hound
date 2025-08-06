import uuid


def get_guid(cluster, scope, kube_type, name, namespace=uuid.NAMESPACE_DNS):
    name = f"kubecluster/{cluster}/{scope}/{kube_type}/{name}"
    return str(uuid.uuid5(namespace, name))
