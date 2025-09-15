from typing_extensions import Annotated
from kubernetes import client, config
from models.k8s.pod import Pod
from models.k8s.namespace import Namespace
from models.k8s.node import Node
from models.k8s.role import Role
from models.k8s.cluster import Cluster
from models.k8s.cluster_role import ClusterRole
from models.k8s.resource import Resource
from models.k8s.resource_group import ResourceGroup, GroupVersion
from models.k8s.role_binding import RoleBinding
from models.k8s.cluster_role_binding import ClusterRoleBinding
from models.k8s.endpoint_slice import EndpointSlice
from models.k8s.service import Service
from models.k8s.identities import User, Group
from models.k8s.dynamic import DynamicResource
from models.eks.user import IAMUser
from utils.helpers import DumpClient
from utils.mapper import NamespaceResourceMapper
from models.k8s.service_account import ServiceAccount
from collections import defaultdict
from pathlib import Path
import typer
from enum import Enum

dump_app = typer.Typer()


config.load_kube_config()

OutputPath = Annotated[
    Path,
    typer.Argument(
        exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True
    ),
]


class OutputFormat(str, Enum):
    json = "json"
    ndjson = "ndjson"


IDENTITY_MAPPING = {"User": User, "Group": Group}


@dump_app.callback()
def main(
    ctx: typer.Context,
    output_format: OutputFormat = typer.Option(
        OutputFormat.json, "--format", case_sensitive=False
    ),
):
    ctx.ensure_object(dict)
    ctx.obj["dump_client"] = DumpClient(base_dir=Path("./output"), mode=output_format)


@dump_app.command()
def namespaces(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj["dump_client"]

    v1 = client.CoreV1Api()
    namespaces = v1.list_namespace()
    # kv_lookup = {}
    for ns in namespaces.items:
        ns_object = Namespace(**ns.to_dict())
        dump_client.write(
            ns_object,
            name=ns_object.metadata.name,
            resource="namespaces",
            namespace=None,
        )

    # kv_path = f"{output_dir}/rel/namespaces.json"
    # dump_client.to_json(kv_path, json.dumps(kv_lookup), output_dir)


@dump_app.command()
def pods(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj["dump_client"]

    v1 = client.CoreV1Api()
    pods = v1.list_pod_for_all_namespaces()
    for pod in pods.items:
        pod_object = Pod(**pod.to_dict())
        dump_client.write(
            pod_object,
            name=pod_object.metadata.name,
            resource="pods",
            namespace=pod_object.metadata.namespace,
        )


@dump_app.command()
def nodes(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj["dump_client"]

    v1 = client.CoreV1Api()
    nodes = v1.list_node()
    kv_lookup = {}
    for node in nodes.items:
        node_object = Node(**node.to_dict())
        kv_lookup[node_object.metadata.name] = node_object.metadata.uid
        dump_client.write(
            node_object,
            name=node_object.metadata.name,
            resource="nodes",
            namespace=None,
        )

    # kv_path = f"{output_dir}/rel/nodes.json"
    # dump_client.to_json(kv_path, json.dumps(kv_lookup), output_dir)


@dump_app.command()
def cluster(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj["dump_client"]

    conf = config.list_kube_config_contexts()[1]
    cluster_object = Cluster(name=conf["context"]["cluster"])
    dump_client.write(
        cluster_object, name=cluster_object.name, resource="clusters", namespace=None
    )
    # dump_client.to_json(f"{output_dir}/rel/cluster.json", cluster_object.model_dump_json(indent=2), output_dir)


@dump_app.command()
def role_bindings(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj["dump_client"]

    v1 = client.RbacAuthorizationV1Api()
    rolebs = v1.list_role_binding_for_all_namespaces()
    for roleb in rolebs.items:
        roleb_object = RoleBinding(**roleb.to_dict())
        dump_client.write(
            roleb_object,
            name=roleb_object.metadata.name,
            resource="role_bindings",
            namespace=roleb_object.metadata.namespace,
        )
        for subject in roleb_object.subjects:
            if subject.kind in ["User", "Group"]:
                subject_object = IDENTITY_MAPPING[subject.kind](**subject.model_dump())
                dump_client.write(
                    subject_object,
                    name=subject_object.name.lower(),
                    resource=subject.kind.lower(),
                    namespace=roleb_object.metadata.namespace,
                )


@dump_app.command()
def roles(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj["dump_client"]

    v1 = client.RbacAuthorizationV1Api()
    roles = v1.list_role_for_all_namespaces()
    kv_lookup = defaultdict(dict)
    for role in roles.items:
        role_object = Role(**role.to_dict())
        kv_lookup[role_object.metadata.namespace][
            role_object.metadata.name
        ] = role_object.metadata.uid
        dump_client.write(
            role_object,
            name=role_object.metadata.name,
            resource="roles",
            namespace=role_object.metadata.namespace,
        )

    # kv_path = f"{output_dir}/rel/roles.json"
    # dump_client.to_json(kv_path, json.dumps(kv_lookup), output_dir)


@dump_app.command()
def cluster_roles(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj["dump_client"]

    v1 = client.RbacAuthorizationV1Api()
    roles = v1.list_cluster_role()
    kv_lookup: dict[str, str] = {}
    for role in roles.items:
        role_object = ClusterRole(**role.to_dict())
        kv_lookup[role_object.metadata.name] = role_object.metadata.uid
        dump_client.write(
            role_object,
            name=role_object.metadata.name,
            resource="cluster_roles",
            namespace=None,
        )

    # kv_path = f"{output_dir}/rel/cluster_roles.json"
    # dump_client.to_json(kv_path, json.dumps(kv_lookup), output_dir)


@dump_app.command()
# @process_external_identities(output_dir="./output", scope="cluster")
def cluster_role_bindings(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj["dump_client"]

    v1 = client.RbacAuthorizationV1Api()
    rolebs = v1.list_cluster_role_binding()
    for roleb in rolebs.items:
        roleb_object = ClusterRoleBinding(**roleb.to_dict())
        dump_client.write(
            roleb_object,
            name=roleb_object.metadata.name,
            resource="cluster_role_bindings",
            namespace=None,
        )

        for subject in roleb_object.subjects:
            if subject.kind in ["User", "Group"]:
                subject_object = IDENTITY_MAPPING[subject.kind](**subject.model_dump())
                dump_client.write(
                    subject_object,
                    name=subject_object.name,
                    resource=subject.kind.lower(),
                    namespace=None,
                )


@dump_app.command()
def service_accounts(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj["dump_client"]

    v1 = client.CoreV1Api()
    service_accounts = v1.list_service_account_for_all_namespaces()
    kv_lookup = defaultdict(dict)

    for service_account in service_accounts.items:
        sa_object = ServiceAccount(**service_account.to_dict())
        kv_lookup[sa_object.metadata.namespace][
            sa_object.metadata.name
        ] = sa_object.metadata.uid
        dump_client.write(
            sa_object,
            name=sa_object.metadata.name,
            resource="serviceaccounts",
            namespace=sa_object.metadata.namespace,
        )

    # kv_path = f"{output_dir}/rel/service_accounts.json"
    # dump_client.to_json(kv_path, json.dumps(kv_lookup), output_dir)


@dump_app.command()
def endpoint_slices(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj["dump_client"]

    v1 = client.DiscoveryV1Api()
    endpoint_slices = v1.list_endpoint_slice_for_all_namespaces()
    kv_lookup = defaultdict(list)
    for es in endpoint_slices.items:
        es_object = EndpointSlice(**es.to_dict())
        kv_lookup[es_object.metadata.labels.service_name].append(es_object.metadata.uid)
        dump_client.write(
            es_object,
            name=es_object.metadata.name,
            resource="endpoint_slices",
            namespace=es_object.metadata.namespace,
        )

    # kv_path = f"{output_dir}/rel/endpoint-slices.json"
    # dump_client.to_json(kv_path, json.dumps(kv_lookup), output_dir)


@dump_app.command()
def services(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj["dump_client"]

    v1 = client.CoreV1Api()
    services = v1.list_service_for_all_namespaces()
    for service in services.items:
        service_object = Service(**service.to_dict())
        dump_client.write(
            service_object,
            name=service_object.metadata.name,
            resource="services",
            namespace=service_object.metadata.namespace,
        )


@dump_app.command()
def crds(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj["dump_client"]

    api = client.ApisApi()
    custom = client.CustomObjectsApi()

    # kv_lookup = defaultdict(dict)
    groups = api.get_api_versions()
    for group in groups.groups:
        group_object = ResourceGroup(**group.to_dict())
        dump_client.write(
            group_object,
            name=f"{group_object.name}",
            resource="api_groups",
            namespace=None,
        )

        resources = custom.get_api_resources(
            group=group_object.name, version=group_object.preferred_version.version
        )
        for resource in resources.to_dict()["resources"]:
            resource_object = Resource(
                **resource, api_group_name=group.name, api_group_uid=group_object.uid
            )
            dump_client.write(
                resource_object,
                name=f"{group.name}/{resource_object.name}",
                resource="api_resources",
                namespace=None,
            )
            # kv_lookup[group_object.name][resource_object.name] = resource_object.uid

    v1 = client.CoreV1Api()
    core_resources = v1.get_api_resources()
    for core_resource in core_resources.resources:
        core_group = ResourceGroup(
            name="__core__",
            preferred_version=GroupVersion(group_version="v1", version="v1"),
            versions=[GroupVersion(group_version="v1", version="v1")],
        )
        dump_client.write(
            core_group, name=core_group.name, resource="api_groups", namespace=None
        )

        core_resource_object = Resource(
            **core_resource.to_dict(),
            api_group_name=core_group.name,
            api_group_uid=core_group.uid,
        )
        dump_client.write(
            core_group,
            name=core_resource_object.name,
            resource="core_resources",
            namespace=None,
        )

        # kv_lookup[core_group.name][core_resource_object.name] = core_resource_object.uid

    # kv_output_path = f"{output_dir}/rel/api_resources.json"
    # dump_client.to_json(kv_output_path, json.dumps(kv_lookup, indent=2), output_dir)


# @dump_app.command()
# def dynamic(output_dir: OutputPath):
#     mapper = NamespaceResourceMapper("./output/api_resources")
#     get_api_groups = glob.glob("./output/api_groups/*.json")

#     for api_group in get_api_groups:
#         with open(api_group, "r") as inputapi:
#             api_obj = json.loads(inputapi.read())
#         mapper.api_groups[api_obj["name"]] = api_obj


#     get_roles = glob.glob("./output/namespaces/**/roles/*.json")
#     for role in get_roles:
#         with open(role, "r") as inputrole:
#             role_json = json.loads(inputrole.read())
#             role_obj = Role(**role_json)
#         if role_obj.rules:
#             for rule in role_obj.rules:
#                 find_resources = mapper.discover_resources_for_rule(
#                     rule, role_obj.metadata.namespace
#                 )
#                 for resource in find_resources:
#                     if resource["kind"] == "Secret":
#                         permissions = [permission.value for permission in rule.verbs]
#                         source_role = {"name": role_obj.metadata.name, "uid": role_obj.metadata.uid,
#                                     "permissions": permissions}
#                         dynamic_resource = DynamicResource(**resource, role=source_role)
#                         resource_output_path = f"{output_dir}/namespaces/{dynamic_resource.metadata.namespace}/dynamic/{dynamic_resource.metadata.name}.json"
#                         dump_client.to_json(resource_output_path, dynamic_resource.model_dump_json(indent=2), output_dir)


@dump_app.command()
def all(ctx: typer.Context, output_dir: OutputPath):
    dump_functions = [
        ("cluster", cluster),
        ("namespaces", namespaces),
        ("nodes", nodes),
        ("pods", pods),
        ("roles", roles),
        ("rolebindings", role_bindings),
        ("cluster_roles", cluster_roles),
        ("cluster_role_bindings", cluster_role_bindings),
        ("service_accounts", service_accounts),
        ("endpoint_slices", endpoint_slices),
        ("services", services),
        ("core_resources", crds),
    ]
    for name, func in dump_functions:
        typer.echo(f"Dumping {name}…")
        ctx.invoke(func, ctx, output_dir=output_dir)
