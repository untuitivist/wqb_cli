# WQB CLI

`wqb` is an agent-first WorldQuant BRAIN CLI.
It provides two clearly separated capabilities:

- API commands call `https://api.worldquantbrain.com`.
- Local-data commands read files under `local/`.

Local data is produced outside this package by the WebDataScope browser plugin: [leetesla/WebDataScope-WorldQuant](https://github.com/leetesla/WebDataScope-WorldQuant).
The CLI does not directly read browser/plugin cache.

## Repository Layout

```text
.
  cli.py
  commands/                 command groups
  core/                     HTTP, auth, config, registry, IO, local data
  resources/
    api_inventory/          bundled endpoint registry and generated API docs
    docs/
      commands/             hand-authored CLI docs and real examples
      generated/            generated notes
  tests/                    CLI smoke tests
  local/                    user-local runtime data, ignored by Git
  pyproject.toml
```

The Python package name is still `wqb_cli`.
`pyproject.toml` maps that package to this repository root.

## Install

Python 3.11 or newer is expected.
The local workflow has been run with a Conda environment named `WQBRAIN`.

```powershell
conda activate WQBRAIN
python -m pip install -e .
```

## Authentication

Create a local `.env` file:

```powershell
Copy-Item .env.example local/.env
```

Set either `EMAIL` / `PASSWORD` or `WQB_EMAIL` / `WQB_PASSWORD`.

Login:

```powershell
wqb auth login --execute
```

Cookies are stored under:

```text
local/auth/cookies.json
```

## API Commands

API commands use the bundled registry:

```text
resources/api_inventory/api_inventory_complete.json
```

Examples:

```powershell
wqb api stats
wqb api list
wqb api show /authentication
wqb api call GET /authentication
wqb auth status
wqb sim options
```

Mutating requests require `--execute`.
There is no dry-run mode.
If a mutating command is run without `--execute`, the CLI returns `ok: false` with `reason: mutating_method_requires_execute`.

## Local Data Import

Local data is not bundled and must not be committed.
All local data belongs under `local/`.

Expected structure:

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

`data_all` comes from the WebDataScope plugin-provided network-disk data package.
Download it separately and place the files directly under:

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

Use `scope` commands to inspect it:

```powershell
wqb scope files
wqb scope list
wqb scope top USA_1 --group datafield --min-count 5 --limit 10
wqb scope pickle-summary USA_1 --sample 1
wqb scope alpha-rows USA_1 --table os --datafield volume --limit 3 --columns id,sharpe,fitness,turnover,margin
```

### community

Community data is built from a WebDataScope export.
The flow is:

1. Use WebDataScope to export community data as `WQPCommunityState_*.json` or `WQPCommunityState_*.wqcs`.
2. Put the exported file under `local/community/`.
3. Run `wqb community export` to build `community.sqlite3`.
4. Query the generated SQLite database.

Build SQLite:

```powershell
wqb community export --source local/community/WQPCommunityState_20260520_103908.json
```

If `--source` is omitted, the CLI uses the newest `WQPCommunityState_*.json` or `*.wqcs` it can find in local export locations.

Query examples:

```powershell
wqb community stats
wqb community search alpha --limit 3
wqb community search neutralization --scope docs --limit 2
```

## Command Documentation

Command docs live under:

```text
resources/docs/commands/
```

Useful entry points:

- `resources/docs/commands/README.md`
- `resources/docs/commands/local-data/README.md`
- `resources/docs/commands/community/README.md`
- `resources/docs/commands/scope/README.md`
- `resources/docs/commands/simulations/create/examples/backtest_modes.md`

API inventory docs live under:

```text
resources/api_inventory/
```

## Simulation Rules

Backtest modes and concurrency rules are documented in:

```text
resources/docs/commands/simulations/create/examples/backtest_modes.md
```

Current operating constraints:

- `REGULAR_FASTEXPR_MULTI` single request supports up to 10 expressions.
- Recommended `REGULAR_FASTEXPR_MULTI` batch size: 10 when `region != "GLB"`, 5 when `region == "GLB"`.
- `REGULAR_PYTHON` cannot use multi-simulation.
- `SUPER` uses one SUPER POST body per simulation.
- Concurrent `SUPER` simulation requests: at most 3.
- Concurrent `REGULAR` simulation requests: at most 8 when `region != "GLB"`, at most 4 when `region == "GLB"`.

## Development

Run smoke tests:

```powershell
python -m unittest discover -s tests
```

Build package:

```powershell
python -m build
```

Do not commit:

- `.env`
- `local/.env`
- `local/auth/`
- `local/community/*.sqlite3`
- `local/community/WQPCommunityState_*.json`
- `local/community/WQPCommunityState_*.wqcs`
- `local/data_all/`
- `dist/`
- `build/`
- `*.egg-info/`
