from kubepyhound.models.graph import GraphEntries, Graph
from kubepyhound.models.entries import Node as GraphNode
from kubepyhound.models.icons import CustomNode, CustomNodeIcon, CustomNodeType
from kubepyhound.models.k8s.cluster import ClusterNode
from kubepyhound.models.k8s.node import NodeOutput
from kubepyhound.models.k8s.namespace import NamespaceNode
from kubepyhound.models.k8s.role_binding import RoleBindingNode
from kubepyhound.models.k8s.cluster_role_binding import ClusterRoleBindingNode
from kubepyhound.models.k8s.pod import PodNode
from kubepyhound.models.k8s.role import RoleNode
from kubepyhound.models.k8s.identities import UserNode, GroupNode
from kubepyhound.models.k8s.cluster_role import ClusterRoleNode
from kubepyhound.models.k8s.service_account import ServiceAccountNode
from kubepyhound.models.k8s.resource_group import ResourceGroupNode
from kubepyhound.models.k8s.resource import ResourceNode, CustomResourceNode
from kubepyhound.models.k8s.statefulset import StatefulSetNode
from kubepyhound.models.k8s.replicaset import ReplicaSetNode
from kubepyhound.models.k8s.deployment import DeploymentNode
from kubepyhound.models.k8s.daemonset import DaemonSetNode
from kubepyhound.models.k8s.generic import GenericNode
from kubepyhound.models.k8s.stale import StaleNode
from kubepyhound.models.k8s.dynamic import DynamicNode
from kubepyhound.models.eks.user import IAMUserNode
from kubepyhound.models.k8s.volume import VolumeNode
from typing_extensions import Annotated
from dataclasses import dataclass
from pathlib import Path
from kubepyhound.utils.helpers import load_json, process_stale_refs
from rich.progress import Progress
from typing import Type, TypeVar
from kubepyhound.utils.api import BloodHound
from kubepyhound.utils.lookup import LookupManager
import duckdb
import glob
import typer

T = TypeVar("T", bound=GraphNode)
E = TypeVar("E", bound=GraphEntries)

KUBE_ICONS = {
    "K8sCluster": "globe",
    "K8sNode": "server",
    "K8sPod": "cube",
    "K8sReplicaSet": "cubes",
    "K8sDeployment": "cubes",
    "K8sStatefulSet": "cubes",
    "K8sDaemonSet": "cubes",
    "K8sNamespace": "folder",
    "K8sRole": "id-badge",
    "K8sRoleBinding": "link",
    "K8sClusterRole": "id-badge",
    "K8sClusterRoleBinding": "link",
    "K8sScopedRole": "id-badge",
    "K8sScopedRoleBinding": "link",
    "K8sServiceAccount": "user-cog",
    "K8sUser": "user",
    "AWSIAMUser": "user",
    "K8sGroup": "user-group",
    "K8sResource": "gear",
    "K8sResourceGroup": "gears",
    "K8sSecret": "key",
    "K8sVolume": "folder",
}

sync_app = typer.Typer()
convert_app = typer.Typer()


@dataclass
class SyncOptions:
    input: Path
    session: BloodHound
    cluster: str
    lookup: LookupManager
    job_id: int | None = None
    mode: str = "sync"


@dataclass
class ConvertOptions:
    input: Path
    output: Path
    cluster: str
    lookup: LookupManager
    mode: str = "convert"


class ResourceGraph:
    def __init__(
        self,
        files: list[str],
        model_class: Type[T],
        lookup: LookupManager,
        cluster: str,
    ):
        self.files = files
        self.model_class = model_class
        self.cluster = cluster

        self.lookup = lookup
        self._graph: Graph | None = None

    @property
    def graph(self) -> Graph:
        if self._graph is not None:
            return self._graph

        graph_entries = GraphEntries()
        with Progress() as progress:
            task = progress.add_task(
                f"Converting {len(self.files)} {self.model_class.__name__}s",
                total=len(self.files),
            )
            for resource in self.files:
                node = self.model_class.from_input(**load_json(resource))
                node._lookup = self.lookup
                node._cluster = self.cluster
                graph_entries.nodes.append(node)
                for edge in node.edges:
                    graph_entries.edges.append(edge)
                progress.advance(task)

        self._graph = Graph(graph=graph_entries)
        return self._graph

    def to_file(self, output_path: Path) -> None:
        with open(output_path, "w") as outputfile:
            outputfile.write(
                self.graph.model_dump_json(
                    exclude_unset=False, indent=2, exclude_none=True
                )
            )

    def to_bloodhound(self, session: BloodHound, ctx: SyncOptions) -> None:
        if not ctx.job_id:
            ctx.job_id = session.start_upload_job()

        session.upload_graph(
            ctx.job_id,
            self.graph.model_dump_json(
                exclude_unset=False, indent=2, exclude_none=True
            ),
        )


def process_resources(
    resource_files: list[str],
    model_class: Type[T],
    options: ConvertOptions | SyncOptions,
):
    if not resource_files:
        return None

    graph = ResourceGraph(
        files=resource_files,
        model_class=model_class,
        lookup=options.lookup,
        cluster=options.cluster,
    )
    # TODO: This can probably be done more... more pythonic
    if isinstance(options, ConvertOptions):
        output_file = options.output / f"{model_class.__name__.lower()}.json"
        graph.to_file(output_file)

    if isinstance(options, SyncOptions):
        graph.to_bloodhound(options.session, options)


@sync_app.callback()
def sync_callback(
    ctx: typer.Context,
    input: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=False,
            dir_okay=True,
            writable=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    bhe_uri: Annotated[str, typer.Option(envvar="BHE_URI")],
    token_id: Annotated[str, typer.Option(envvar="BHE_API_ID")],
    token_key: Annotated[str, typer.Option(envvar="BHE_API_KEY")],
):
    lookup = LookupManager()
    lookup.con = duckdb.connect(database="k8s.duckdb", read_only=False)
    session = BloodHound(token_id=token_id, token_key=token_key, bhe_uri=bhe_uri)
    cluster_metadata = load_json(f"{input}/cluster/cluster.json")
    cluster_id = cluster_metadata["name"]
    ctx.obj = SyncOptions(input, session, lookup=lookup, cluster=cluster_id)

    def _close_upload_job():
        if ctx.obj.job_id is not None:
            ctx.obj.session.stop_upload_job(ctx.obj.job_id)

    ctx.call_on_close(_close_upload_job)


@convert_app.callback()
def convert_callback(
    ctx: typer.Context,
    input: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=False,
            dir_okay=True,
            writable=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=False,
            dir_okay=True,
            writable=False,
            readable=True,
            resolve_path=True,
        ),
    ],
):
    lookup = LookupManager()
    lookup.con = duckdb.connect(database="k8s.duckdb", read_only=False)
    cluster_metadata = load_json(f"{input}/cluster/cluster.json")
    ctx.obj = ConvertOptions(
        input, output=output, lookup=lookup, cluster=cluster_metadata["name"]
    )


@sync_app.command()
@convert_app.command()
def cluster(ctx: typer.Context):
    resource_files = glob.glob(f"{ctx.obj.input}/cluster/*.json", recursive=True)
    process_resources(resource_files, ClusterNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def namespaces(ctx: typer.Context):
    resource_files = glob.glob(f"{ctx.obj.input}/namespaces/*.json", recursive=True)
    process_resources(resource_files, NamespaceNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def nodes(ctx: typer.Context):
    resource_files = glob.glob(f"{ctx.obj.input}/nodes/*.json", recursive=True)
    process_resources(resource_files, NodeOutput, ctx.obj)


@sync_app.command()
@convert_app.command()
def pods(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj.input}/namespaces/**/pods/*.json", recursive=True
    )
    process_resources(resource_files, PodNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def roles(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj.input}/namespaces/**/roles/*.json", recursive=True
    )
    process_resources(resource_files, RoleNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def volumes(ctx: typer.Context):
    resource_files = glob.glob(f"{ctx.obj.input}/volumes/*.json", recursive=True)
    process_resources(resource_files, VolumeNode, ctx.obj)


@sync_app.command()
@convert_app.command()
# @process_stale_refs("rolebindings", output_dir="./output")
def role_bindings(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj.input}/namespaces/**/role_bindings/*.json",
        recursive=True,
    )
    process_resources(resource_files, RoleBindingNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def cluster_roles(ctx: typer.Context):
    resource_files = glob.glob(f"{ctx.obj.input}/cluster_roles/*.json", recursive=True)
    process_resources(resource_files, ClusterRoleNode, ctx.obj)


@sync_app.command()
@convert_app.command()
# @process_stale_refs("rolebindings", output_dir="./output")
def cluster_role_bindings(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj.input}/cluster_role_bindings/*.json", recursive=True
    )
    process_resources(resource_files, ClusterRoleBindingNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def stale(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj.input}/stale_objects/**/*.json", recursive=True
    )
    process_resources(resource_files, StaleNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def resource_groups(ctx: typer.Context):
    resource_files = glob.glob(f"{ctx.obj.input}/api_groups/**/*.json", recursive=True)
    process_resources(resource_files, ResourceGroupNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def custom_resource_definitions(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj.input}/custom_resource_definitions/**/*.json",
        recursive=True,
    )
    process_resources(resource_files, CustomResourceNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def resource_definitions(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj.input}/resource_definitions/**/*.json", recursive=True
    )
    process_resources(resource_files, ResourceNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def service_accounts(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj.input}/namespaces/**/serviceaccounts/*.json",
        recursive=True,
    )
    process_resources(resource_files, ServiceAccountNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def groups(ctx: typer.Context):
    resource_files = glob.glob(f"{ctx.obj.input}/group/*.json", recursive=True)
    process_resources(resource_files, GroupNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def users(ctx: typer.Context):
    resource_files = glob.glob(f"{ctx.obj.input}/user/*.json", recursive=True)
    process_resources(resource_files, UserNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def statefulsets(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj.input}/namespaces/**/statefulsets/*.json", recursive=True
    )
    process_resources(resource_files, StatefulSetNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def deployments(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj.input}/namespaces/**/deployments/*.json", recursive=True
    )
    process_resources(resource_files, DeploymentNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def replicasets(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj.input}/namespaces/**/replicasets/*.json", recursive=True
    )
    process_resources(resource_files, ReplicaSetNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def daemonsets(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj.input}/namespaces/**/daemonsets/*.json", recursive=True
    )
    process_resources(resource_files, DaemonSetNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def eks(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj.input}/identities/aws/**/*.json", recursive=True
    )
    process_resources(resource_files, IAMUserNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def dynamic(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj.input}/namespaces/**/dynamic/*.json", recursive=True
    )
    process_resources(resource_files, DynamicNode, ctx.obj)


@sync_app.command()
@convert_app.command()
def generic(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj.input}/namespaces/*/unmapped/**/*.json", recursive=True
    )
    resource_files += glob.glob(f"{ctx.obj.input}/unmapped/**/*.json", recursive=True)
    process_resources(resource_files, GenericNode, ctx.obj)


@sync_app.command()
def icons(ctx: typer.Context):
    for node_name, icon_name in KUBE_ICONS.items():
        # if node_name.startswith("AWS"):
        #     node_icon = CustomNodeIcon(
        #         type="font-awesome", name=icon_name, color="#F4B942"
        #     )
        # else:
        node_icon = CustomNodeIcon(type="font-awesome", name=icon_name, color="#FFFFFF")
        node_type = CustomNodeType(icon=node_icon)
        custom_type = {"custom_types": {node_name: node_type}}
        custom = CustomNode(**custom_type)
        ctx.obj.session.custom_node(custom.model_dump_json())


@sync_app.command()
@convert_app.command()
def all(ctx: typer.Context):
    sync_functions = [
        ("cluster", cluster),
        ("namespaces", namespaces),
        ("nodes", nodes),
        ("pods", pods),
        ("deployments", deployments),
        ("daemonsets", daemonsets),
        ("replicasets", replicasets),
        ("statefulsets", statefulsets),
        ("users", users),
        ("groups", groups),
        ("roles", roles),
        ("resource_groups", resource_groups),
        ("rolebindings", role_bindings),
        ("cluster_roles", cluster_roles),
        ("cluster_role_bindings", cluster_role_bindings),
        ("service_accounts", service_accounts),
        ("resource_definitions", resource_definitions),
        ("custom_resource_definitions", custom_resource_definitions),
        ("generic", generic),
    ]

    for _, func in sync_functions:
        ctx.invoke(func)
