from typing_extensions import Annotated
from kubernetes import client, config
from kubernetes.dynamic import DynamicClient
from kubepyhound.models.k8s.pod import Pod
from kubepyhound.models.k8s.namespace import Namespace
from kubepyhound.models.k8s.node import Node
from kubepyhound.models.k8s.role import Role
from kubepyhound.models.k8s.cluster import Cluster
from kubepyhound.models.k8s.cluster_role import ClusterRole
from kubepyhound.models.k8s.resource import Resource
from kubepyhound.models.k8s.resource_group import ResourceGroup, GroupVersion
from kubepyhound.models.k8s.role_binding import RoleBinding
from kubepyhound.models.k8s.cluster_role_binding import ClusterRoleBinding
from kubepyhound.models.k8s.endpoint_slice import EndpointSlice
from kubepyhound.models.k8s.service import Service
from kubepyhound.models.k8s.identities import User, Group
from kubepyhound.models.k8s.dynamic import DynamicResource
from kubepyhound.models.eks.user import IAMUser
from kubepyhound.utils.helpers import DumpClient
from kubepyhound.utils.mapper import NamespaceResourceMapper
from kubepyhound.models.k8s.generic import Generic
from kubepyhound.models.k8s.service_account import ServiceAccount
from pathlib import Path
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
import duckdb
import typer
import glob
from enum import Enum
from dataclasses import dataclass
from rich.console import Console
from functools import wraps


IDENTITY_MAPPING = {"User": User, "Group": Group}
RESOURCE_TYPES = {
    "Pod": Pod,
    "ServiceAccount": ServiceAccount,
    "Role": Role,
    "Node": Node,
    "Namespace": Namespace,
    "RoleBinding": RoleBinding,
    "ClusterRole": ClusterRoleBinding,
    "ClusterRoleBinding": Cluster,
    # "Service": ServiceNode
}


@dataclass
class Options:
    client: DumpClient


class OutputFormat(str, Enum):
    simple = "simple"
    ndjson = "ndjson"


OutputPath = Annotated[
    Path,
    typer.Argument(
        exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True
    ),
]

dump_app = typer.Typer()
config.load_kube_config()


@dump_app.callback()
def main(
    ctx: typer.Context,
    output_format: OutputFormat = typer.Option(
        OutputFormat.simple, "--format", case_sensitive=False
    ),
):
    ctx.obj = Options(
        client=DumpClient(base_dir=Path("./output"), mode=output_format.value)
    )


def progress_handler(task_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(ctx: typer.Context, *args, **kwargs):
            console = Console()
            with Progress(
                SpinnerColumn(),
                TextColumn("{task.description}"),
                TimeElapsedColumn(),
                transient=False,
                console=console,
            ) as task_progress:
                task_id = task_progress.add_task(
                    f"Collecting {task_name}...", total=None
                )
                result = func(ctx, *args, **kwargs)
                task_progress.update(
                    task_id,
                    description=f"Collecting {task_name}: complete ({result})",
                    refresh=True,
                )
            return result

        return wrapper

    return decorator


@dump_app.command()
@progress_handler("namespaces")
def namespaces(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj.client
    resource_count = 0

    v1 = client.CoreV1Api()
    namespaces = v1.list_namespace()
    for ns in namespaces.items:
        ns_object = Namespace(**ns.to_dict())
        dump_client.write(
            ns_object,
            name=ns_object.metadata.name,
            resource="namespaces",
            namespace=None,
        )
        resource_count += 1
    return resource_count


@dump_app.command()
@progress_handler("pods")
def pods(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj.client
    resource_count = 0

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
        resource_count += 1

    return resource_count


@dump_app.command()
@progress_handler("nodes")
def nodes(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj.client
    resource_count = 0

    v1 = client.CoreV1Api()
    nodes = v1.list_node()
    for node in nodes.items:
        node_object = Node(**node.to_dict())
        dump_client.write(
            node_object,
            name=node_object.metadata.name,
            resource="nodes",
            namespace=None,
        )
        resource_count += 1
    return resource_count


@dump_app.command()
@progress_handler("cluster")
def cluster(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj.client
    conf = config.list_kube_config_contexts()[1]
    cluster_object = Cluster(name=conf["context"]["cluster"])
    dump_client.write(
        cluster_object, name="cluster", resource="cluster", namespace=None
    )
    return 1


@dump_app.command()
@progress_handler("role-bindings")
def role_bindings(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj.client
    resource_count = 0

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
        resource_count += 1
        for subject in roleb_object.subjects:
            if subject.kind in ["User", "Group"]:
                subject_object = IDENTITY_MAPPING[subject.kind](**subject.model_dump())
                dump_client.write(
                    subject_object,
                    name=subject_object.name.lower(),
                    resource=subject.kind.lower(),
                    namespace=roleb_object.metadata.namespace,
                )
    return resource_count


@dump_app.command()
@progress_handler("roles")
def roles(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj.client
    resource_count = 0

    v1 = client.RbacAuthorizationV1Api()
    roles = v1.list_role_for_all_namespaces()
    for role in roles.items:
        role_object = Role(**role.to_dict())
        dump_client.write(
            role_object,
            name=role_object.metadata.name,
            resource="roles",
            namespace=role_object.metadata.namespace,
        )
        resource_count += 1
    return resource_count


@dump_app.command()
@progress_handler("cluster-roles")
def cluster_roles(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj.client
    resource_count = 0

    v1 = client.RbacAuthorizationV1Api()
    roles = v1.list_cluster_role()
    for role in roles.items:
        role_object = ClusterRole(**role.to_dict())
        dump_client.write(
            role_object,
            name=role_object.metadata.name,
            resource="cluster_roles",
            namespace=None,
        )
        resource_count += 1
    return resource_count


@dump_app.command()
@progress_handler("cluster role-bindings")
def cluster_role_bindings(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj.client
    resource_count = 0

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
        resource_count += 1

        for subject in roleb_object.subjects:
            if subject.kind in ["User", "Group"]:
                subject_object = IDENTITY_MAPPING[subject.kind](**subject.model_dump())
                dump_client.write(
                    subject_object,
                    name=subject_object.name,
                    resource=subject.kind.lower(),
                    namespace=None,
                )
    return resource_count


@dump_app.command()
@progress_handler("service accounts")
def service_accounts(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj.client
    resource_count = 0

    v1 = client.CoreV1Api()
    service_accounts = v1.list_service_account_for_all_namespaces()
    for service_account in service_accounts.items:
        sa_object = ServiceAccount(**service_account.to_dict())
        dump_client.write(
            sa_object,
            name=sa_object.metadata.name,
            resource="serviceaccounts",
            namespace=sa_object.metadata.namespace,
        )
        resource_count += 1
    return resource_count


@dump_app.command()
@progress_handler("endpoint slices")
def endpoint_slices(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj.client
    resource_count = 0

    v1 = client.DiscoveryV1Api()
    endpoint_slices = v1.list_endpoint_slice_for_all_namespaces()
    for es in endpoint_slices.items:
        es_object = EndpointSlice(**es.to_dict())
        dump_client.write(
            es_object,
            name=es_object.metadata.name,
            resource="endpoint_slices",
            namespace=es_object.metadata.namespace,
        )
        resource_count += 1
    return resource_count


@dump_app.command()
@progress_handler("services")
def services(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj.client
    resource_count = 0

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
        resource_count += 1
    return resource_count


@dump_app.command()
@progress_handler("custom resource definitions")
def custom_resource_definitions(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj.client
    resource_count = 0

    api = client.ApisApi()
    custom = client.CustomObjectsApi()

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
                resource="custom_resource_definitions",
                namespace=None,
            )
            resource_count += 1

    return resource_count


@dump_app.command()
@progress_handler("resource definitions")
def resource_definitions(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj.client
    resource_count = 0

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
            core_resource_object,
            name=core_resource_object.name,
            resource="resource_definitions",
            namespace=None,
        )
        resource_count += 1
    return resource_count


@dump_app.command()
@progress_handler("unmapped resources")
def generic(ctx: typer.Context, output_dir: OutputPath):
    dump_client: DumpClient = ctx.obj.client
    resource_count = 0

    api_client = client.ApiClient()
    dyn_client = DynamicClient(api_client)

    discovered_resources = dyn_client.resources.search()
    for resource in discovered_resources:
        # Only check for resources that support the list command and or not of kind *List
        if not resource.kind.endswith("List") and "list" in resource.verbs:
            resource_client = dyn_client.resources.get(
                api_version=resource.api_version, kind=resource.kind
            )
            items = resource_client.get()
            for item in items.items:
                generic_model = Generic(**item.to_dict())
                if not generic_model.kind in RESOURCE_TYPES:
                    resource_count += 1
                    dump_client.write(
                        generic_model,
                        name=generic_model.metadata.name,
                        resource=f"unmapped/{generic_model.kind}",
                        namespace=generic_model.metadata.namespace,
                    )

    return resource_count


@dump_app.command()
def bootstrap(
    # This may be used later for some extra enrichment sauce
    queries_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=True,
            readable=True,
            resolve_path=True,
        ),
    ] = Path("kubepyhound/duckdb/tables"),
):
    bootstrap_files = glob.glob(f"{queries_path}/*.sql")
    con = duckdb.connect(database="k8s.duckdb", read_only=False)
    for query in bootstrap_files:
        with open(query, "r") as query_file:
            sql_content = query_file.read()
            con.execute(sql_content)
    con.close()


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
        # ("endpoint_slices", endpoint_slices),
        ("services", services),
        ("resource_definitions", resource_definitions),
        ("custom_resource_definitions", custom_resource_definitions),
    ]

    for _, func in dump_functions:
        ctx.invoke(func, ctx, output_dir=output_dir)
