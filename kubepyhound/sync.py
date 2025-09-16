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


def process_resources(
    resource_files: list[str], model_class: Type[T], bloodhound, preview: bool
):
    graph_entries = GraphEntries()

    stale_refs = []
    for resource in resource_files:
        node = model_class.from_input(**load_json(resource))
        graph_entries.nodes.append(node)
        for edge in node.edges:
            graph_entries.edges.append(edge)
        stale_refs.extend(node._stale_collection.stale_refs)

    graph = Graph(graph=graph_entries)
    typer.echo("Finalized node and edge convertion")
    if preview:
        with open("graph.json", "w") as outputfile:
            outputfile.write(graph.model_dump_json(exclude_unset=False, indent=2))
        typer.echo("Generated graph as graph.json")

    else:
        bloodhound.upload(graph.model_dump_json(exclude_unset=False))
        typer.echo("Uploaded Graph file to bloodhound")

    return stale_refs


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
    preview: str = typer.Option(
        default=True,
        help="Generate an OpenGraph file without uploading it to BloodHound",
    ),
):
    ctx.obj = {
        "input_path": input,
        "bloodhound": BloodHound(
            token_id=token_id, token_key=token_key, bhe_uri=bhe_uri
        ),
        "preview": preview,
    }


@sync_app.command()
def cluster(ctx: typer.Context):
    with open(f"{ctx.obj['input_path']}/cluster.json", "r") as f:
        json_object = json.loads(f.read())

    parsed_type = ClusterNode.from_input(**json_object)
    entries = GraphEntries(nodes=[parsed_type], edges=[])
    graph = Graph(graph=entries)

    with open("graph.json", "w") as outfile:
        outfile.write(graph.model_dump_json(exclude_unset=False))
    ctx.obj["bloodhound"], ctx.obj["preview"].upload(
        graph.model_dump_json(exclude_unset=False)
    )


@sync_app.command()
def namespaces(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}//namespaces/*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} namespaces")
    return process_resources(
        resource_files, NamespaceNode, ctx.obj["bloodhound"], ctx.obj["preview"]
    )


@sync_app.command()
def nodes(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}/nodes/ip-*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} nodes")
    return process_resources(
        resource_files, NodeOutput, ctx.obj["bloodhound"], ctx.obj["preview"]
    )


@sync_app.command()
def pods(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}/namespaces/**/pods/*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} pods")
    return process_resources(
        resource_files, PodNode, ctx.obj["bloodhound"], ctx.obj["preview"]
    )


@sync_app.command()
def roles(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}/namespaces/**/roles/*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} roles")
    return process_resources(
        resource_files, RoleNode, ctx.obj["bloodhound"], ctx.obj["preview"]
    )


@sync_app.command()
@process_stale_refs("rolebindings", output_dir="./output")
def role_bindings(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}/namespaces/**/role_bindings/*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} rolebindings")
    return process_resources(
        resource_files, RoleBindingNode, ctx.obj["bloodhound"], ctx.obj["preview"]
    )


@sync_app.command()
def cluster_roles(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}/cluster_roles/*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} cluster roles")
    return process_resources(
        resource_files, ClusterRoleNode, ctx.obj["bloodhound"], ctx.obj["preview"]
    )


@sync_app.command()
@process_stale_refs("rolebindings", output_dir="./output")
def cluster_role_bindings(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}/cluster_role_bindings/*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} cluster rolebindings")
    return process_resources(
        resource_files,
        ClusterRoleBindingNode,
        ctx.obj["bloodhound"],
        ctx.obj["preview"],
    )


@sync_app.command()
def stale(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}/stale_objects/**/*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} stale resources")
    return process_resources(
        resource_files, StaleNode, ctx.obj["bloodhound"], ctx.obj["preview"]
    )


@sync_app.command()
def resource_groups(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}/api_groups/**/*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} resource groups")
    return process_resources(
        resource_files, ResourceGroupNode, ctx.obj["bloodhound"], ctx.obj["preview"]
    )


@sync_app.command()
def custom_resource_definitions(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}/custom_resource_definitions/**/*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} custom resources")
    return process_resources(
        resource_files, ResourceNode, ctx.obj["bloodhound"], ctx.obj["preview"]
    )


@sync_app.command()
def resource_definitions(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}/resource_definitions/**/*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} core resources")
    return process_resources(
        resource_files, ResourceNode, ctx.obj["bloodhound"], ctx.obj["preview"]
    )


@sync_app.command()
def service_accounts(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}/namespaces/**/serviceaccounts/*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} service accounts")
    return process_resources(
        resource_files, ServiceAccountNode, ctx.obj["bloodhound"], ctx.obj["preview"]
    )


@sync_app.command()
def groups(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}/identities/groups/*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} external groups")
    return process_resources(
        resource_files, GroupNode, ctx.obj["bloodhound"], ctx.obj["preview"]
    )


@sync_app.command()
def users(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}/identities/users/*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} external users")
    return process_resources(
        resource_files, UserNode, ctx.obj["bloodhound"], ctx.obj["preview"]
    )


@sync_app.command()
def eks(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}/identities/aws/**/*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} AWS IAM identities")
    return process_resources(
        resource_files, IAMUserNode, ctx.obj["bloodhound"], ctx.obj["preview"]
    )


@sync_app.command()
def dynamic(ctx: typer.Context):
    resource_files = glob.glob(
        f"{ctx.obj['input_path']}/namespaces/**/dynamic/*.json", recursive=True
    )
    typer.echo(f"Found {len(resource_files)} dynamic resources")
    return process_resources(
        resource_files, DynamicNode, ctx.obj["bloodhound"], ctx.obj["preview"]
    )


@sync_app.command()
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
        response = ctx.obj["bloodhound"], ctx.obj["preview"].custom_node(
            custom.model_dump_json()
        )
        print(response.json())
    typer.echo("Synced custom icons with bloodhound")


@sync_app.command()
def all(ctx: typer.Context):
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
        ("resource_definitions", resource_definitions),
        ("custom_resource_definitions", custom_resource_definitions),
    ]
    for name, func in dump_functions:
        typer.echo(f"Syncing {name}…")
        ctx.invoke(func, ctx)
