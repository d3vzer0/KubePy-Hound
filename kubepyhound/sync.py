from kubepyhound.models.graph import GraphEntries, Node as GraphNode, MetaData, Graph
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
from kubepyhound.models.k8s.resource import ResourceNode
from kubepyhound.models.k8s.stale import StaleNode
from kubepyhound.models.k8s.dynamic import DynamicNode
from kubepyhound.models.eks.user import IAMUserNode
from typing_extensions import Annotated
from dataclasses import dataclass
from pathlib import Path
from kubepyhound.utils.helpers import load_json, process_stale_refs
from typing import Type, TypeVar, Protocol, Optional
from pydantic import Field, BaseModel, create_model
import glob
import typer
from kubepyhound.utils.api import BloodHound
import json

T = TypeVar("T", bound=GraphNode)
E = TypeVar("E", bound=GraphEntries)

KUBE_ICONS = {
    "KubeCluster": "globe",
    "KubeNode": "server",
    "KubePod": "cube",
    "KubeNamespace": "folder",
    "KubeRole": "id-badge",
    "KubeRoleBinding": "link",
    "KubeClusterRole": "id-badge",
    "KubeClusterRoleBinding": "link",
    "KubeScopedRole": "id-badge",
    "KubeScopedRoleBinding": "link",
    "KubeServiceAccount": "user-cog",
    "KubeUser": "user",
    "AWSIAMUser": "user",
    "KubeGroup": "user-group",
    "KubeResource": "gear",
    "KubeResourceGroup": "gears",
    "KubeSecret": "key",
}


sync_app = typer.Typer()
convert_app = typer.Typer()


@dataclass
class SyncOptions:
    input: Path
    session: BloodHound
    job_id: int | None = None
    mode: str = "sync"


@dataclass
class ConvertOptions:
    input: Path
    output: Path
    mode: str = "convert"


class ResourceGraph:
    def __init__(self, files: list[str], model_class: Type[T]):
        self.files = files
        self.model_class = model_class

    @property
    def graph(self) -> Graph:
        graph_entries = GraphEntries()
        for resource in self.files:
            node = self.model_class.from_input(**load_json(resource))
            graph_entries.nodes.append(node)
            for edge in node.edges:
                graph_entries.edges.append(edge)
            # stale_refs.extend(node._stale_collection.stale_refs)
        return Graph(graph=graph_entries)

    def to_file(self, output_path: Path) -> None:
        with open(output_path, "w") as outputfile:
            outputfile.write(self.graph.model_dump_json(exclude_unset=False, indent=2))
            typer.echo(f"Generated graph as {output_path}")

    def to_bloodhound(self, session: BloodHound, ctx: SyncOptions) -> None:
        if not ctx.job_id:
            ctx.job_id = session.start_upload_job()
            print(ctx.job_id)

        session.upload_graph(
            ctx.job_id, self.graph.model_dump_json(exclude_unset=False, indent=2)
        )


def process_resources(
    resource_files: list[str],
    model_class: Type[T],
    options: ConvertOptions | SyncOptions,
):
    graph = ResourceGraph(files=resource_files, model_class=model_class)
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
    session = BloodHound(token_id=token_id, token_key=token_key, bhe_uri=bhe_uri)
    ctx.obj = SyncOptions(input, session)


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
    ctx.obj = ConvertOptions(input, output=output)


def shared_commands(app: typer.Typer):
    @app.command()
    def cluster(ctx: typer.Context):
        resource_files = glob.glob(f"{ctx.obj.input}/cluster/*.json", recursive=True)
        typer.echo(f"Found {len(resource_files)} cluster")
        return process_resources(resource_files, ClusterNode, ctx.obj)

    @app.command()
    def namespaces(ctx: typer.Context):
        resource_files = glob.glob(f"{ctx.obj.input}/namespaces/*.json", recursive=True)
        typer.echo(f"Found {len(resource_files)} namespaces")
        return process_resources(resource_files, NamespaceNode, ctx.obj)

    @app.command()
    def nodes(ctx: typer.Context):
        resource_files = glob.glob(f"{ctx.obj.input}/nodes/ip-*.json", recursive=True)
        typer.echo(f"Found {len(resource_files)} nodes")
        return process_resources(resource_files, NodeOutput, ctx.obj)

    @app.command()
    def pods(ctx: typer.Context):
        resource_files = glob.glob(
            f"{ctx.obj.input}/namespaces/**/pods/*.json", recursive=True
        )
        typer.echo(f"Found {len(resource_files)} pods")
        return process_resources(resource_files, PodNode, ctx.obj)

    @app.command()
    def roles(ctx: typer.Context):
        resource_files = glob.glob(
            f"{ctx.obj.input}/namespaces/**/roles/*.json", recursive=True
        )
        typer.echo(f"Found {len(resource_files)} roles")
        return process_resources(resource_files, RoleNode, ctx.obj)

    @app.command()
    # @process_stale_refs("rolebindings", output_dir="./output")
    def role_bindings(ctx: typer.Context):
        resource_files = glob.glob(
            f"{ctx.obj.input}/namespaces/**/role_bindings/*.json",
            recursive=True,
        )
        typer.echo(f"Found {len(resource_files)} rolebindings")
        return process_resources(resource_files, RoleBindingNode, ctx.obj)

    @app.command()
    def cluster_roles(ctx: typer.Context):
        resource_files = glob.glob(
            f"{ctx.obj.input}/cluster_roles/*.json", recursive=True
        )
        typer.echo(f"Found {len(resource_files)} cluster roles")
        return process_resources(resource_files, ClusterRoleNode, ctx.obj)

    @app.command()
    # @process_stale_refs("rolebindings", output_dir="./output")
    def cluster_role_bindings(ctx: typer.Context):
        resource_files = glob.glob(
            f"{ctx.obj.input}/cluster_role_bindings/*.json", recursive=True
        )
        typer.echo(f"Found {len(resource_files)} cluster rolebindings")
        return process_resources(resource_files, ClusterRoleBindingNode, ctx.obj)

    @app.command()
    def stale(ctx: typer.Context):
        resource_files = glob.glob(
            f"{ctx.obj.input}/stale_objects/**/*.json", recursive=True
        )
        typer.echo(f"Found {len(resource_files)} stale resources")
        return process_resources(resource_files, StaleNode, ctx.obj)

    @app.command()
    def resource_groups(ctx: typer.Context):
        resource_files = glob.glob(
            f"{ctx.obj.input}/api_groups/**/*.json", recursive=True
        )
        typer.echo(f"Found {len(resource_files)} resource groups")
        return process_resources(resource_files, ResourceGroupNode, ctx.obj)

    @app.command()
    def custom_resource_definitions(ctx: typer.Context):
        resource_files = glob.glob(
            f"{ctx.obj.input}/custom_resource_definitions/**/*.json",
            recursive=True,
        )
        typer.echo(f"Found {len(resource_files)} custom resources")
        return process_resources(resource_files, ResourceNode, ctx.obj)

    @app.command()
    def resource_definitions(ctx: typer.Context):
        resource_files = glob.glob(
            f"{ctx.obj.input}/resource_definitions/**/*.json", recursive=True
        )
        typer.echo(f"Found {len(resource_files)} core resources")
        return process_resources(resource_files, ResourceNode, ctx.obj)

    @app.command()
    def service_accounts(ctx: typer.Context):
        resource_files = glob.glob(
            f"{ctx.obj.input}/namespaces/**/serviceaccounts/*.json",
            recursive=True,
        )
        typer.echo(f"Found {len(resource_files)} service accounts")
        return process_resources(resource_files, ServiceAccountNode, ctx.obj)

    @app.command()
    def groups(ctx: typer.Context):
        resource_files = glob.glob(
            f"{ctx.obj.input}/identities/groups/*.json", recursive=True
        )
        typer.echo(f"Found {len(resource_files)} external groups")
        return process_resources(resource_files, GroupNode, ctx.obj)

    @app.command()
    def users(ctx: typer.Context):
        resource_files = glob.glob(
            f"{ctx.obj.input}/identities/users/*.json", recursive=True
        )
        typer.echo(f"Found {len(resource_files)} external users")
        return process_resources(resource_files, UserNode, ctx.obj)

    @app.command()
    def eks(ctx: typer.Context):
        resource_files = glob.glob(
            f"{ctx.obj.input}/identities/aws/**/*.json", recursive=True
        )
        typer.echo(f"Found {len(resource_files)} AWS IAM identities")
        return process_resources(resource_files, IAMUserNode, ctx.obj)

    @app.command()
    def dynamic(ctx: typer.Context):
        resource_files = glob.glob(
            f"{ctx.obj.input}/namespaces/**/dynamic/*.json", recursive=True
        )
        typer.echo(f"Found {len(resource_files)} dynamic resources")
        return process_resources(resource_files, DynamicNode, ctx.obj)

    @app.command()
    def icons(ctx: typer.Context):
        typer.echo(f"Found {len(KUBE_ICONS.keys())} custom icons")
        for node_name, icon_name in KUBE_ICONS.items():
            if node_name.startswith("AWS"):
                node_icon = CustomNodeIcon(
                    type="font-awesome", name=icon_name, color="#F4B942"
                )
            else:
                node_icon = CustomNodeIcon(
                    type="font-awesome", name=icon_name, color="#FFFFFF"
                )
            node_type = CustomNodeType(icon=node_icon)
            custom_type = {"custom_types": {node_name: node_type}}
            custom = CustomNode(**custom_type)
            response = ctx.obj.session.custom_node(custom.model_dump_json())
        typer.echo("Synced custom icons with bloodhound")

    @app.command()
    def all(ctx: typer.Context):
        dump_functions = [
            ("cluster", cluster),
            ("namespaces", namespaces),
            ("nodes", nodes),
            ("pods", pods),
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
            ("icons", icons),
        ]
        for name, func in dump_functions:
            typer.echo(f"Syncing {name}…")
            ctx.invoke(func, ctx)

        if isinstance(ctx.obj, SyncOptions) and ctx.obj.job_id:
            ctx.obj.session.stop_upload_job(ctx.obj.job_id)
