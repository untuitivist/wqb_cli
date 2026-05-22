# wqb-cli

English | [简体中文](README_CN.md)

`wqb-cli` is an agent-native command line toolkit for working with the WorldQuant BRAIN API and local research data.

It is built for coding agents and long-running research agents first, not as a thin human-only wrapper. Commands produce structured JSON, preserve raw API context, wait for asynchronous platform results, and fit naturally into repeatable research workflows: authentication, API discovery, alpha listing and inspection, simulation submission, alpha submission checks, local `data_all` screening, and community-data search.

- Repository: [untuitivist/wqb_cli](https://github.com/untuitivist/wqb_cli)
- Author: [wiz](https://github.com/untuitivist)
- License: GPL-3.0-only with Commons Clause. See [LICENSE](LICENSE).

## Agent-Native Design

`wqb-cli` is designed so an agent can operate it safely and inspectably without relying on browser state or manual clicking:

- Structured command outputs that can be saved with `--output` and consumed by later workflow nodes.
- Explicit wait semantics for simulations, submit checks, alpha checks, recordsets, and other asynchronous API results.
- Bundled API inventory and command docs so agents can inspect available endpoints locally.
- Reusable workflow node documents under `workflow/`, with clear inputs, allowed commands, required outputs, and success criteria.
- Local data commands that read stable files under `local/` instead of scraping browser/plugin caches directly.
- Raw request and response context preserved in command output, including status codes, parameters, locations, retry events, and result bodies.
- No dry-run branch to confuse automation: commands either call the API, wait for the requested result, or fail clearly.

## What This Tool Provides

- API commands for `https://api.worldquantbrain.com`.
- Auth helpers that store cookies locally.
- Simulation commands for REGULAR FASTEXPR, REGULAR PYTHON, and SUPER backtests.
- Alpha commands for listing, checking, recordsets, correlations, and submit workflows.
- Local data commands for `data_all` / `all_data.pickle` screening.
- Local community-data import and search commands.
- Bundled endpoint inventory and command documentation.
- Workflow documents for structured research nodes under `workflow/`.

## Important Notes

- This project is not affiliated with WorldQuant or WorldQuant BRAIN.
- Mutating commands send real API requests. There is no dry-run mode.
- Commands that need asynchronous results wait for completion or fail on timeout. Simulation-style waits default to 900 seconds where applicable.
- Local data files are intentionally not committed. Keep credentials, cookies, community exports, and `data_all` files under `local/`.
- The license is source-available but not OSI open source because Commons Clause restricts selling the software.

## Requirements

- Python 3.11 or newer.
- A WorldQuant BRAIN account.
- Windows PowerShell is the primary tested shell.
- Recommended local Conda environment: `WQBRAIN`.

## Installation

Clone the repository:

```powershell
git clone https://github.com/untuitivist/wqb_cli.git
cd wqb_cli
```

Install in editable mode:

```powershell
conda activate WQBRAIN
python -m pip install -e .
```

Confirm the CLI is available:

```powershell
wqb --help
wqb auth status
```

If `wqb` is not on `PATH`, run commands through Python from the parent directory:

```powershell
python -m wqb_cli --help
```

## Package Metadata

The Python distribution name is `wqb-cli`.

The import/package name is `wqb_cli`.

The command line entry point is:

```powershell
wqb
```

Current package version:

```toml
version = "0.3.1"
```

## Authentication

Create a local environment file:

```powershell
New-Item -ItemType Directory -Force local
Copy-Item .env.example local/.env
```

Fill in one of the following credential pairs:

```text
EMAIL=...
PASSWORD=...
```

or:

```text
WQB_EMAIL=...
WQB_PASSWORD=...
```

Login:

```powershell
wqb auth login
```

Check authentication:

```powershell
wqb auth status
```

Cookies are stored locally:

```text
local/auth/cookies.json
```

Do not commit `local/`, `.env`, or cookie files.

## Repository Layout

```text
.
  cli.py
  commands/                 CLI command groups
  core/                     HTTP, auth, config, registry, IO, local stores
  resources/
    api_inventory/          Bundled API endpoint inventory
    docs/
      commands/             Handwritten command docs and examples
      generated/            Generated command references
  workflow/                 Research workflow node documents
  tests/                    Test suite
  local/                    User-local runtime data, ignored by Git
  LICENSE
  pyproject.toml
  README.md
```

## Common API Commands

Inspect the bundled API inventory:

```powershell
wqb api stats
wqb api list
wqb api show /authentication
wqb api params /users/self/alphas
```

Call a safe endpoint:

```powershell
wqb api call GET /authentication
```

Inspect simulation options:

```powershell
wqb sim options
```

Most high-level query commands expose common filters directly and still allow raw query parameters through `--param KEY=VALUE`.

Examples:

```powershell
wqb alpha list --settings-neutralization SUBINDUSTRY --is-sharpe ">=1.25"
wqb data fields --dataset analyst14 --coverage ">0.8" --order=-userCount
wqb data datasets --category pv --region USA --delay 1 --limit 20
```

When in doubt, check command help:

```powershell
wqb alpha list --help
wqb data datasets --help
wqb data fields --help
wqb data operators --help
wqb sim create --help
```

## Alpha Listing Examples

Recent ACTIVE REGULAR alphas for a region/delay:

```powershell
wqb alpha list `
  --type REGULAR `
  --settings-region CHN `
  --settings-delay 1 `
  --settings-instrument-type EQUITY `
  --limit 100 `
  --order=-dateSubmitted `
  --status ACTIVE
```

Tower-tag lookup, when tags are maintained:

```powershell
wqb alpha list `
  --type REGULAR `
  --settings-region CHN `
  --settings-delay 1 `
  --settings-instrument-type EQUITY `
  --limit 100 `
  --order=-dateSubmitted `
  --status ACTIVE `
  --tag CHN/D1/PV
```

If the tag result is empty or inconsistent, fall back to the region/delay query and inspect `pyramids[].name` locally.

Do not rely on `--param pyramid=pv` for alpha listing. It is accepted by the server but does not filter results in observed tests.

## Simulation Workflows

Create a simulation from a JSON body:

```powershell
wqb sim create --input body.json --output simulation_result.json
```

By default, `sim create` waits for the simulation result or fails on timeout. For multi-simulation requests, child simulations are also waited and reported.

Get an existing simulation:

```powershell
wqb sim get <simulation_id> --max-wait-seconds 900 --output simulation.json
```

Simulation examples are documented here:

```text
resources/docs/commands/simulations/create/examples/input_json.md
resources/docs/commands/simulations/create/examples/backtest_modes.md
```

Supported documented example bodies include:

- REGULAR FASTEXPR multi-simulation.
- REGULAR FASTEXPR single simulation.
- REGULAR PYTHON single simulation.
- SUPER simulation.

For REGULAR FASTEXPR multi-simulation, the shared settings requirement is limited to:

- `delay`
- `region`
- `instrumentType`
- `language`

## Submit Workflow

Submit an alpha:

```powershell
wqb alpha submit <alpha_id> --output submit_result.json
```

The CLI distinguishes API acceptance from final submit success.

- `201 Created` means the submit request was accepted by the API.
- Final success requires polling the submit/check result until the submit check succeeds.
- If an intermediate response is printed, it should be read as `201 Created, waiting for results...`.

Commands that wait for platform-side results return only after a final result, a request failure, or timeout.

## Local Data Setup

Local data is not bundled and must not be committed.

Recommended layout:

```text
local/
  .env
  config.json
  auth/
    cookies.json
  community/
    WQPCommunityState_*.json
    WQPCommunityState_*.wqcs
    community.sqlite3
  data_all/
    info_data.bin
    all_data.pickle
    main.ipynb
```

### data_all

`data_all` comes from the WebDataScope plugin's network-disk data package:

[leetesla/WebDataScope-WorldQuant](https://github.com/leetesla/WebDataScope-WorldQuant)

`all_data.pickle` is not released with this repository. Download it from the Baidu Netdisk link provided by the WebDataScope plugin README, then place it under:

```text
local/data_all/
```

Expected files:

```text
local/data_all/
  info_data.bin
  all_data.pickle
  main.ipynb
```

Check local data:

```powershell
wqb scope files
wqb scope list
wqb scope show USA_1 --output local/scope_usa_1.json
wqb scope top USA_1 --group datafield --min-count 5 --limit 10
wqb scope pickle-summary USA_1 --sample 1
wqb scope alpha-rows USA_1 --table os --datafield volume --limit 3 --columns id,sharpe,fitness,turnover,margin
```

### Community Data

Community data is imported from WebDataScope exports.

1. Export community data from WebDataScope as `WQPCommunityState_*.json` or `WQPCommunityState_*.wqcs`.
2. Put the export under `local/community/`.
3. Build the local SQLite database.
4. Query the generated database.

Build SQLite:

```powershell
wqb community export --source local/community/WQPCommunityState_20260520_103908.json
```

If `--source` is omitted, the CLI searches for the latest `WQPCommunityState_*.json` or `*.wqcs` under the local community directory.

Query examples:

```powershell
wqb community stats
wqb community search alpha --limit 3
wqb community search neutralization --scope docs --limit 2
```

## Research Workflow Documents

The structured workflow is documented under:

```text
workflow/
```

Each node describes:

- required inputs
- allowed CLI commands
- required outputs
- success criteria
- next nodes

The main graph is:

```text
workflow/workflow_graph.md
```

Node F is responsible for datafield feasibility. It now prefers tower tags such as `CHN/D1/PV` to discover existing ACTIVE REGULAR alphas, then falls back to region/delay full scans and local `pyramids[].name` inspection.

## Command Documentation

Command documentation lives in:

```text
resources/docs/commands/
```

Useful entry points:

- `resources/docs/commands/README.md`
- `resources/docs/commands/local-data/README.md`
- `resources/docs/commands/community/README.md`
- `resources/docs/commands/scope/README.md`
- `resources/docs/commands/simulations/create/examples/backtest_modes.md`
- `resources/docs/commands/simulations/create/examples/input_json.md`

Bundled API inventory:

```text
resources/api_inventory/
```

## Development

Install editable package:

```powershell
python -m pip install -e .
```

Run tests from the repository root:

```powershell
$env:PYTHONPATH='U:\Project\MainCode\3.Work\WQB'
python -m pytest tests
```

Build package artifacts:

```powershell
python -m build
```

Do not commit:

- `.env`
- `local/`
- `dist/`
- `build/`
- `*.egg-info/`
- credentials or cookies

## Troubleshooting

### `ModuleNotFoundError: No module named 'wqb_cli'`

Run tests with the parent directory on `PYTHONPATH`:

```powershell
$env:PYTHONPATH='U:\Project\MainCode\3.Work\WQB'
python -m pytest tests
```

Or install editable mode again:

```powershell
python -m pip install -e .
```

### `WARNING: Ignoring invalid distribution ~qb-cli`

This is usually a stale pip uninstall/install artifact under `site-packages`. If the install succeeds, it does not block normal use. To clean it, inspect the active environment's `Lib/site-packages` directory and remove stale `~qb*` distribution folders.

### `wqb.exe is installed ... which is not on PATH`

Use the full Python module form or add the printed scripts directory to `PATH`:

```powershell
python -m wqb_cli --help
```

## Release

Current release:

[wqb-cli 0.3.1](https://github.com/untuitivist/wqb_cli/releases/tag/v0.3.1)

Release checklist:

1. Update `version` in `pyproject.toml`.
2. Run editable install.
3. Run tests.
4. Commit changes.
5. Tag the release, for example `v0.3.1`.
6. Push the branch and tag.
7. Publish a GitHub Release.

## License

This project is licensed under GPL-3.0-only with the Commons Clause License Condition v1.0.

Required attribution:

```text
Original author: wiz
Original repository: https://github.com/untuitivist/wqb_cli
Author GitHub: https://github.com/untuitivist
```

The Commons Clause removes the right to sell the software as defined in [LICENSE](LICENSE). This means the source is available, but the project is not OSI open source.
