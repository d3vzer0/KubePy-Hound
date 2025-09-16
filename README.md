# WIP: KubePy-Hound

KubePy-Hound is a Python CLI that collects Kubernetes resources and converts them into
BloodHound OpenGraph data. It is built with [Typer](https://typer.tiangolo.com/) and designed to
be run either locally against a kubeconfig or as part of an automated collection pipeline.

**Note:** Very very very- WIP. Use with caution, under active development but wanted to publish this either way while working on the project :) 

## Features

- Export core Kubernetes resources, RBAC objects, and CRDs to JSON or NDJSON
- Build BloodHound OpenGraph files from the exported resources
- Toggle output format globally via a single `--format` switch
- Packageable CLI (`kubepy-hound`) with `uv`-managed dependencies

## Installation

The project is managed with [uv](https://github.com/astral-sh/uv). To install the CLI in the
current environment:

```bash
uv pip install --editable .
```

This will expose the console script `kubepy-hound`. You can also run the app without
installing by creating a virtual environment and running the script directly using:

```bash
python main.py <command> <args>
```

> **Note**: The CLI loads your active kubeconfig (`~/.kube/config`) via the Kubernetes Python
> client. Ensure the environment running the dump commands has the necessary cluster access.

## Usage

All commands share the same top-level options. The most important one is `--format`, which
selects whether resources are stored as indented JSON (`json`) or newline-delimited JSON
(`ndjson`). The option must be provided before the subcommand name.

```bash
kubepy-hound --format ndjson dump namespaces ./output
```

### Dump commands

```
kubepy-hound dump --help
```

The `dump` namespace collects Kubernetes resources into the `output` directory by default
(configurable via the `output_dir` argument). Notable commands include:

- `kubepy-hound dump all ./output` – run the full collection suite sequentially
- `kubepy-hound dump cluster ./output` – record information about the current cluster
- `kubepy-hound dump namespaces ./output` – export namespaces
- `kubepy-hound dump pods ./output` – export pods across all namespaces
- `kubepy-hound dump roles ./output` – export namespaced roles
- `kubepy-hound dump role-bindings ./output` – export role bindings and discovered identities
- `kubepy-hound dump cluster-roles ./output` – export cluster-wide roles
- `kubepy-hound dump cluster-role-bindings ./output` – export cluster role bindings
- `kubepy-hound dump service-accounts ./output` – export service accounts
- `kubepy-hound dump services ./output` – export services
- `kubepy-hound dump resource-definitions ./output` – export core API resources
- `kubepy-hound dump custom-resource-definitions ./output` – export custom resources

Each command writes to a folder structure under `./output` (or your specified directory). For
example, pods are emitted to `output/namespaces/<namespace>/pods/<pod>.json`.

### Sync commands

The `sync` namespace transforms collected resources into BloodHound graph JSON.

Before running sync commands, set the BloodHound Enterprise API credentials as environment
variables:

```bash
export BHE_URI="https://bloodhound.example.com"
export BHE_API_ID="your-id"
export BHE_API_KEY="your-key"
```

Then run a sync command against a previously generated dump directory:

```bash
kubepy-hound sync --input ./output
kubepy-hound sync namespaces
kubepy-hound sync pods
```

The sync pipeline produces `graph.json` and can optionally upload the graph via the
BloodHound Enterprise API client.

## Development

Create an isolated environment and install dependencies:

```bash
uv venv
source .venv/bin/activate
uv pip install -e .[dev]  # if you add development extras
```

Run the CLI from source during development:

```bash
uv run python main.py dump namespaces ./output
uv run python main.py sync namespaces --input ./output
```

## Packaging & Release

- Build distributable artifacts with `uv build`
- Verify the wheel exports the `kubepy-hound` console script before release

## Project Structure

- `dump.py` – Typer app for resource collection
- `sync.py` – Typer app for graph generation and BloodHound upload
- `models/` – Pydantic models representing Kubernetes objects and BloodHound nodes
- `utils/` – helper utilities (`DumpClient`, BloodHound API client, lookup helpers)
- `output/` – default location for collected data (ignored in version control)


## Other projects and noteable mentions

- [BloodHound](https://github.com/SpecterOps/BloodHound) - BloodHound leverages graph theory to reveal hidden and often unintended relationships across identity and access management systems. Powered by OpenGraph, BloodHound now supports comprehensive analysis beyond Active Directory and Azure environments, enabling users to map complex privilege relationships across diverse identity platforms
- [KubeHound](https://kubehound.io/) - KubeHound creates a graph of attack paths in a Kubernetes cluster, allowing you to identify direct and multi-hop routes an attacker is able to take, visually or through complex graph queries - uses Neptune and Gremlin for storage and querying.

## License

Distributed under the MIT License. See `LICENSE` for details.
