# WQB CLI

This repository contains two related pieces:

- `wqb_core`: a Python wrapper around common WorldQuant BRAIN endpoints.
- `workflow/nodes`: an agent-oriented research workflow for selecting a tower, screening datasets and datafields, forming hypotheses, generating expressions, running simulations, diagnosing results, and preparing final submission actions.

The workflow is intentionally file based. Each node has its own `node.md`, `SKILL.md`, `run.bat`, and, where needed, scripts under `scripts/`. Runtime outputs are written under `docs/research_runs/` and should not be committed.

## Repository Layout

```text
wqb_core/          Python package for BRAIN API sessions and endpoint mixins
workflow/          Research workflow graph, reusable node specs, and node scripts
docs/data_all/     Local dataset metadata used by screening nodes
docs/research_runs/ Runtime output directory, ignored by Git
```

## Setup

Python 3.11 or newer is expected. The local workflow has been run with a Conda environment named `WQBRAIN`.

```powershell
conda create -n WQBRAIN python=3.12 -y
conda activate WQBRAIN
python -m pip install -e .
```

Create local credentials from the template:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` and set either `EMAIL` / `PASSWORD` or `WQB_EMAIL` / `WQB_PASSWORD`.

## Authentication State

`wqb_core` can reuse cookies from `.wqb_cli_auth/cookies.json` after a successful login. That directory is local runtime state and is ignored by Git.

## Workflow Usage

The graph is documented in `workflow/workflow_graph.md`. Nodes are designed to be executed in order, but diagnosis nodes can branch back to earlier nodes when a tower, field family, mechanism, or expression structure needs to be revised.

Typical node execution pattern:

```powershell
cd workflow\nodes\E_数据与字段可行性
.\run.bat
```

Node scripts should write JSON and Markdown outputs themselves. `run.bat` should only orchestrate script execution.

## GitHub Hygiene

Commit source files, node definitions, reusable scripts, and stable documentation.

Do not commit:

- `.env`
- `.wqb_cli_auth/`
- `docs/research_runs/`
- `__pycache__/`
- browser profiles such as `wqb_core/.tmp_edge_profile/`

If any of those paths were committed before `.gitignore` existed, remove them from the Git index with `git rm --cached` before pushing.
