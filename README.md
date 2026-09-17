# wqb-cli

<p align="center">
  <img src="docs/assets/wqb_cli_logo.png" alt="wqb-cli logo" width="360">
</p>

English | [简体中文](README_CN.md)

`wqb-cli` is an agent-native command line toolkit for working with the WorldQuant BRAIN API and local research data.

It is built for coding agents and long-running research agents first, not as a thin human-only wrapper. Commands produce structured JSON, preserve raw API context, wait for asynchronous platform results, and fit naturally into repeatable research workflows: authentication, API discovery, alpha listing and inspection, simulation execution, Alpha submission checks, local `data_all` screening, and community-data search.

- Repository: [untuitivist/wqb_cli](https://github.com/untuitivist/wqb_cli)
- Author: [wiz](https://github.com/untuitivist)
- License: GPL-3.0-only with Commons Clause. See [LICENSE](LICENSE).

## Agent-Native Design

`wqb-cli` is designed so an agent can operate it safely and inspectably without relying on browser state or manual clicking:

- Structured command outputs that can be saved with `--output` and consumed by later workflow nodes.
- Explicit wait semantics for simulations, submit checks, alpha checks, recordsets, and other asynchronous API results.
- Bundled API inventory and command docs so agents can inspect available endpoints locally.
- Two isolated workflow document sets under `workflows/`, with clear inputs, allowed commands, required outputs, and success criteria.
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
- Workflow documents for bounded adaptive simulations and durable template-family batches under `workflows/`.

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

Install a regular runtime copy in the WQBRAIN environment:

```powershell
conda activate WQBRAIN
python -m pip install .
```

The checkout is for development and building distributions only. Run production commands from a separate research workspace with WQBRAIN activated, not through the checkout or a development-directory PYTHONPATH. Editable installs belong in a separate development environment, never in the WQBRAIN runtime environment.

Confirm the installed CLI is available from your research workspace:

```powershell
wqb --help
wqb auth status
```

If `wqb` is not on `PATH`, use the activated environment's installed module from the research workspace:

```powershell
python -I -m wqb_cli --help
```

## Command Overview

The built-in commands below are arranged by use case while preserving the actual parser names and hierarchy. Additional installed plugins may expose more commands. `<...>` marks required positional arguments and `[...]` marks optional ones. Named options are omitted from the tree; inspect them with `--help` at each level.

```text
wqb  # WorldQuant BRAIN command-line toolkit
├─ sim                                                           # Create, inspect, and wait for platform simulations
├─ sqlitesimu                                                    # Durable batch simulation engine backed by local SQLite
├─ alpha                                                         # Inspect, analyze, modify, and formally submit Alphas
├─ data                                                          # Explore platform datasets, fields, and operators
├─ auth                                                          # Manage login and authentication sessions
├─ user                                                          # Inspect current-user and user-specific profiles and activity
├─ account                                                       # Access email, password, and account-token workflows
├─ consultant                                                    # Explore consultant information, programs, and guidance
├─ competition                                                   # Explore competitions, rules, rankings, and SPC submissions
├─ event                                                         # Explore platform events
├─ platform                                                      # Explore platform-wide information and resources
├─ tutorial                                                      # Explore platform tutorial content
├─ suggest                                                       # Request platform suggestions using GET or POST
├─ search <query>                                                # Search the platform globally; no subcommands
├─ community                                                     # Search local community SQLite data, not a live forum crawler
├─ scope                                                         # Inspect local historical research data by REGION_DELAY
├─ shortcut (alias: quick)                                       # Run common combined operations
├─ config                                                        # Manage local configuration and inspect platform settings
├─ docs                                                          # Discover bundled CLI documentation
├─ api                                                           # Inspect the local API registry and call registered endpoints
└─ errors                                                        # Access the platform error-reporting endpoint
```

<details>
<summary>Expand the complete command tree</summary>

```text
wqb  # WorldQuant BRAIN command-line toolkit
├─ sim                                                           # Create, inspect, and wait for platform simulations
│  ├─ options                                                    # Inspect available simulation settings
│  ├─ list                                                       # List simulations
│  ├─ get <simulation_id>                                        # Read simulation status or results with retry waits
│  ├─ create                                                     # Create a simulation from --input and wait for results
│  └─ super-selection                                            # Query or invoke Super Alpha selection simulations
├─ sqlitesimu                                                    # Durable batch simulation engine backed by local SQLite
│  ├─ init                                                       # Initialize the simulation database
│  ├─ enqueue <input>                                            # Validate and enqueue a manifest without executing it
│  ├─ run <input>                                                # Enqueue and execute a manifest with durable concurrent workers
│  ├─ resume <run_id>                                            # Resume unfinished work in an existing run
│  ├─ status [run_id]                                            # Inspect one run or recent runs
│  ├─ cancel <run_id>                                            # Cancel a local run while preserving its history
│  ├─ export <run_id>                                            # Export metrics, checks, dated PnL paths, and experiment records
│  ├─ template-validate <input>                                  # Validate template format, metadata, and candidate lineage
│  └─ template-report <input>                                    # Build template analysis reports from a run export
├─ alpha                                                         # Inspect, analyze, modify, and formally submit Alphas
│  ├─ get <alpha_id>                                             # Get Alpha details
│  ├─ list                                                       # List your Alphas with filters and sorting
│  ├─ distribution                                               # Query Alpha distribution information
│  ├─ lists                                                      # Query platform Alpha list information
│  ├─ super-selection                                            # Query Super Alpha selection information
│  ├─ unsubmitted                                                # Query unsubmitted Alpha information
│  ├─ walkthrough                                                # Read the sample Alpha walkthrough
│  ├─ all                                                        # List visible Alphas through the /alphas endpoint
│  ├─ check <alpha_id>                                           # Fetch platform checks and wait for asynchronous results
│  ├─ recordsets <alpha_id>                                      # List available Alpha recordsets
│  ├─ related <alpha_id>                                         # Query related Alphas
│  ├─ recordset <alpha_id> <name>                                # Read a named recordset such as pnl or turnover
│  ├─ pnl <alpha_id>                                             # Read the PnL series
│  ├─ sharpe <alpha_id>                                          # Read the Sharpe series
│  ├─ yearly-stats <alpha_id>                                    # Read yearly statistics
│  ├─ patch <alpha_id>                                           # Update Alpha properties from --input
│  ├─ submit <alpha_id>                                          # Formally submit an Alpha and handle submission waits
│  ├─ correlation                                                # Query Alpha correlations
│  │  ├─ self <alpha_id>                                         # Query self-correlation results
│  │  ├─ base <alpha_id>                                         # Query the base correlations endpoint
│  │  ├─ prod <alpha_id>                                         # Query production-pool correlations
│  │  └─ power-pool <alpha_id>                                   # Query Power Pool correlations
│  └─ performance-comparison <alpha_id>                          # Query performance comparisons
├─ data                                                          # Explore platform datasets, fields, and operators
│  ├─ categories                                                 # List data categories
│  ├─ datasets                                                   # List datasets
│  ├─ dataset <dataset_id>                                       # Get dataset details
│  ├─ fields                                                     # List data fields with filters
│  ├─ fields-summary                                             # Query field summaries
│  ├─ dataset-search                                             # Search datasets using GET or POST
│  ├─ field <field_id>                                           # Get field details
│  └─ operators                                                  # List platform operators
├─ auth                                                          # Manage login and authentication sessions
│  ├─ status                                                     # Query authentication status
│  ├─ head                                                       # Check the authentication endpoint with HEAD
│  ├─ login                                                      # Log in and save authenticated session cookies
│  ├─ logout                                                     # Log out of the platform session
│  ├─ brainlabs                                                  # Call the BrainLabs authentication endpoint
│  ├─ persona                                                    # Call the Persona authentication endpoint
│  ├─ support                                                    # Call the support authentication endpoint
│  └─ workday                                                    # Call the Workday authentication endpoint
├─ user                                                          # Inspect current-user and user-specific profiles and activity
│  ├─ self                                                       # Get your user profile
│  ├─ consultant-summary                                         # Get your consultant summary
│  ├─ messages                                                   # List your messages with filters and pagination
│  ├─ list                                                       # List users
│  ├─ achievements                                               # List your achievements
│  ├─ simulation-activity                                        # Query your simulation activity
│  ├─ pyramid-alphas                                             # Query your pyramid Alpha activity over a date range
│  ├─ pyramid-multipliers                                        # Query your pyramid multipliers over a date range
│  ├─ agreements                                                 # Query your agreements
│  ├─ alphas-summary                                             # Get your Alpha summary
│  ├─ messages-summary                                           # Get your message summary
│  ├─ pyramid-alpha-summary                                      # Get your pyramid Alpha summary
│  ├─ teams                                                      # List your teams
│  ├─ tutorial-steps                                             # Query your tutorial steps
│  ├─ tutorial-summary                                           # Get your tutorial progress summary
│  ├─ consultant-tutorial-summary                                # Get your consultant tutorial progress
│  ├─ consultant-tutorial-patch                                  # Update your consultant tutorial progress
│  ├─ get <user_id>                                              # Get a user profile
│  ├─ user-achievements <user_id>                                # Query a user's achievements
│  ├─ user-activities <user_id>                                  # Query a user's activity
│  ├─ user-diversity <user_id>                                   # Query diversity by region, delay, and data category
│  ├─ user-alphas-options <user_id>                              # Inspect user Alpha endpoint options, not Alpha rows
│  ├─ user-competitions <user_id>                                # Query a user's competitions
│  └─ user-simulation-settings <user_id>                         # Query a user's simulation settings
├─ account                                                       # Access email, password, and account-token workflows
│  ├─ email-change                                               # Email change workflow using GET or POST
│  ├─ email-reverify                                             # Email reverification workflow using GET or POST
│  ├─ email-verify                                               # Email verification workflow using GET or POST
│  ├─ password-change                                            # Password change workflow using GET or POST
│  ├─ password-forgot                                            # Forgot-password workflow using GET or POST
│  ├─ password-reset                                             # Password reset workflow using GET or POST
│  └─ token                                                      # Account token endpoint using GET or POST
├─ consultant                                                    # Explore consultant information, programs, and guidance
│  ├─ get                                                        # Query consultant information
│  ├─ summary                                                    # Query the consultant summary
│  ├─ datasets                                                   # List consultant datasets
│  ├─ dos-and-donts                                              # Read consultant dos and don'ts
│  ├─ faqs                                                       # Read consultant FAQs
│  ├─ osmosis-guide                                              # Read the Osmosis allocation guide
│  ├─ visualization-tool                                         # Read visualization tool information
│  ├─ program                                                    # Read consultant program information
│  ├─ program-language <language>                                # Read consultant program content by language
│  └─ boards                                                     # Explore consultant boards
│     └─ leader                                                  # Query the consultant leaderboard
├─ competition                                                   # Explore competitions, rules, rankings, and SPC submissions
│  ├─ list                                                       # List competitions
│  ├─ get <competition_id>                                       # Get competition details
│  ├─ agreement <competition_id>                                 # Read or submit a competition agreement
│  ├─ leaderboard <identifier>                                   # Query competition or consultant leaderboards and options
│  ├─ guidelines <competition_id>                                # Read competition guidelines through the agreement endpoint
│  ├─ faq <competition_id>                                       # Read the FAQ URL from competition details
│  └─ spc                                                        # Manage SPC prompt submissions
│     ├─ submissions                                             # List SPC submissions
│     ├─ submission-history <submission_id>                      # Read a submission's history
│     ├─ submission-options [submission_id]                      # Inspect submission collection or item options
│     ├─ create-submission                                       # Create an SPC submission
│     └─ update-submission <submission_id>                       # Update an SPC submission
├─ event                                                         # Explore platform events
│  ├─ list                                                       # List events
│  ├─ options                                                    # Inspect event endpoint options
│  └─ get <event_id>                                             # Get event details
├─ platform                                                      # Explore platform-wide information and resources
│  ├─ achievements                                               # List platform achievement definitions
│  ├─ agreements                                                 # Query platform agreements
│  ├─ captcha                                                    # Call the CAPTCHA endpoint
│  ├─ messages                                                   # Query platform messages
│  ├─ tags                                                       # List tags
│  ├─ teams                                                      # List teams
│  ├─ video-courses                                              # List video courses
│  ├─ achievement-icon <achievement_id>                          # Get the achievement icon endpoint response
│  └─ competition-level-icon <competition_level_id>              # Get the competition-level icon endpoint response
├─ tutorial                                                      # Explore platform tutorial content
│  ├─ list                                                       # List tutorials
│  ├─ pages                                                      # List tutorial pages
│  ├─ page <page_id>                                             # Read a tutorial page
│  └─ slug <tutorial_slug>                                       # Read tutorial content by slug
├─ suggest                                                       # Request platform suggestions using GET or POST
│  ├─ examples                                                   # Request example suggestions
│  ├─ expression                                                 # Request expression suggestions
│  ├─ fastexpr                                                   # Request FASTEXPR suggestions
│  └─ fields                                                     # Request field suggestions
├─ search <query>                                                # Search the platform globally; no subcommands
├─ community                                                     # Search local community SQLite data, not a live forum crawler
│  ├─ search <query>                                             # Search local posts, comments, documentation, and articles
│  ├─ export                                                     # Import a WebDataScope community export into local SQLite
│  └─ stats                                                      # Inspect local community database table counts
├─ scope                                                         # Inspect local historical research data by REGION_DELAY
│  ├─ files                                                      # Locate local scope data files
│  ├─ list                                                       # List available scopes such as USA_1
│  ├─ show <scope>                                               # Read a scope summary
│  ├─ top <scope>                                                # Rank fields, datasets, or categories by historical metrics
│  ├─ search <scope> <query>                                     # Search a scope's fields, datasets, or categories
│  ├─ neutralization <scope>                                     # Inspect historical neutralization performance
│  ├─ pickle-summary <scope>                                     # Read a scope summary from the local pickle
│  └─ alpha-rows <scope>                                         # Read historical Alpha attributes, settings, and IS/OS rows
├─ shortcut (alias: quick)                                       # Run common combined operations
│  ├─ whoami                                                     # Check the current authentication session
│  ├─ simulate                                                   # Create a simulation and wait for completion
│  ├─ alpha-report <alpha_id>                                    # Collect Alpha details, checks, correlations, and yearly stats
│  └─ data-fields                                                # Find fields using region, delay, universe, and other filters
├─ config                                                        # Manage local configuration and inspect platform settings
│  ├─ init                                                       # Initialize the local CLI configuration
│  ├─ list                                                       # List local configuration
│  ├─ get <key>                                                  # Read a local configuration key
│  ├─ set <key> <value>                                          # Set a local configuration key
│  ├─ set-secret <key> <value>                                   # Store a secret in the system keyring
│  ├─ platform                                                   # Query platform configuration
│  └─ competition-levels                                         # Query competition-level configuration
├─ docs                                                          # Discover bundled CLI documentation
│  ├─ list                                                       # List documented command nodes
│  └─ show <path>                                                # Read a documentation file
├─ api                                                           # Inspect the local API registry and call registered endpoints
│  ├─ stats                                                      # Show API registry statistics
│  ├─ list                                                       # List registered endpoints, optionally by path prefix
│  ├─ show <path>                                                # Inspect an endpoint definition
│  ├─ params <path>                                              # Inspect query parameter and request-body hints
│  └─ call <method> <path>                                       # Call an endpoint with path variables, parameters, and JSON
└─ errors                                                        # Access the platform error-reporting endpoint
   └─ envelope                                                   # Send an envelope to the platform error collector
```

</details>

### Choosing an Entry Point

- `sim` calls the platform simulation API directly; `sqlitesimu` adds a local database, batch queues, concurrent workers, recovery, and result exports.
- Simulating is not submitting: `sim create` and `sqlitesimu run` launch simulations; `alpha submit` performs formal Alpha submission. The command tree does not imply that research or final eligibility checks have been completed.
- `community` reads local community data and `scope` reads local historical research data, not live platform state. Despite its name, `community export` imports an existing community export into SQLite; it does not crawl the forum.
- `sqlitesimu cancel` manages a local run and preserves history; it does not cancel every simulation already sent to the platform, and it does not bypass an active worker lease by default.
- `api call` invokes registered endpoints directly. Mutating operations send real requests and do not automatically perform higher-level research checks.

### Exploring Help by Level

```text
wqb --help
wqb sim --help
wqb sim create --help
wqb alpha correlation --help
wqb alpha correlation prod --help
wqb sqlitesimu run --help
wqb sqlitesimu template-report --help
```

Global options include `--registry` and `--cookies`; most leaf commands support `--output`. Consult each command's `--help` for filters, input files, wait limits, and concurrency settings. When adding, removing, or changing commands, update both READMEs and verify the trees against the actual parser.

## Package Metadata

The Python distribution name is `wqb-cli`.

The import/package name is `wqb_cli`.

The command line entry point is:

```powershell
wqb
```

Current package version:

```toml
version = "0.4.0"
```

## Authentication

Resolve the installed runtime's local directory, then create or edit its `.env` file. Do not put runtime credentials in the development checkout:

```powershell
$WqbLocal = python -I -c "from wqb_cli.core.paths import LOCAL_ROOT; print(LOCAL_ROOT)"
New-Item -ItemType Directory -Force $WqbLocal
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

Cookies are stored relative to the installed package directory, not the current working directory:

```text
local/auth/cookies.json
```

All `WqbClient` calls automatically recover the session when BRAIN returns
`204`, `401`, or `429`, matching the status predicate used by `wqb.WQBSession`.
The client reloads credentials from config, keyring, or environment, logs in,
persists the refreshed cookie, and replays the rejected request with bounded
retries. Stale BRAIN cookies are cleared before login so old and refreshed
domain variants cannot be sent together. Calls to `/authentication` are
excluded from recursive renewal, and `POST /authentication` succeeds only on
`201`.

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
  workflows/                Isolated simu and batchsimu workflow documents
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

### Durable SQLite Batch Simulations

To let a workflow generate candidates while the CLI independently runs simulations, polls, retries, and persists results:

```powershell
wqb sqlitesimu run candidates.json --output run-result.json
```

For explicit process control, initialize a database, enqueue once, and resume the returned run:

```powershell
wqb sqlitesimu init --db simulations.sqlite3
wqb sqlitesimu enqueue candidates.json --db simulations.sqlite3 --output enqueue-result.json
wqb sqlitesimu resume <run_id> --db simulations.sqlite3 --output worker-result.json
wqb sqlitesimu status <run_id> --db simulations.sqlite3 --output status.json
wqb sqlitesimu export <run_id> --db simulations.sqlite3 --output run-export.json
```

The default database is `local/sqlitesimu/simulations.sqlite3`. Each run retains candidates, batches, simulation locations, errors, Alpha details, and PnL history, and exposes a `simued_alpha_is_pnl` compatibility view for legacy analysis code. Run exports also include structured `pnl_paths` with deduplicated date grids and per-Alpha daily increments so downstream correlation analysis can align observations by date without filling missing values.

Template-family manifests can be validated before enqueue and rendered into a fixed terminal report:

```powershell
wqb sqlitesimu template-validate template-manifest.json --output template-validation.json
wqb sqlitesimu template-report run-export.json --analysis-contract analysis-contract.json --output template-report.json --markdown-output template-report.md
```

The analysis contract can pre-register a direction-invariant discovery screen separately from positive-direction validation. Reverse discoveries are reported as requiring a new simulation and never become final-check candidates from transformed historical metrics.

See `resources/docs/sqlitesimu.md` for the manifest contract, recovery states, exit codes, and explicit differences from the three legacy workers.

The agent-independent template-family lifecycle is defined in `workflows/workflow_batchsimu/`. Its J node enqueues and launches the worker; K/L/M remain blocked until that exact run reaches a terminal state.

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

The `local/` input paths below refer to the installed package's runtime data, not the development checkout. Resolve the directory in the active environment:

```powershell
$WqbLocal = python -I -c "from wqb_cli.core.paths import LOCAL_ROOT; print(LOCAL_ROOT)"
```

Copy data and credentials into that directory when migrating from an editable install. Back up runtime data before package upgrades; keep research outputs and run databases in a separate workspace. Community refreshes must inspect export coverage and preserve existing documentation when a new export omits it.

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
wqb community export --source (Join-Path $WqbLocal "community/WQPCommunityState_20260918_001150.json")
```

If `--source` is omitted, the CLI searches for the latest `WQPCommunityState_*.json` or `*.wqcs` under the local community directory.

Query examples:

```powershell
wqb community stats
wqb community search alpha --limit 3
wqb community search neutralization --scope docs --limit 2
```

## Research Workflow Documents

Two complete, isolated workflows live under `workflows/`:

```text
workflows/
  workflow_simu/          bounded, adaptive A-M research with synchronous wqb sim create
  workflow_batchsimu/     template-family A-M research with agent-independent sqlitesimu execution
```

Each workflow has its own A node, run directory, input/output contracts, graph, and terminal behavior. They do not share A-F artifacts, SQLite databases, node inputs, or control-flow handoffs.

Entry points:

```text
workflows/workflow_simu/workflow_graph.md
workflows/workflow_batchsimu/workflow_graph.md
```

The batch workflow freezes one settings cell, samples each template family without replacement, records full family lineage, and only analyzes density, quality distributions, errors, and actual IS-PnL correlation after the authoritative run is terminal. K selects candidates from the batch's own results, L performs slow final checks, and M is the only node allowed to call `wqb alpha submit`; no candidate or result crosses into the adaptive workflow.

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

Activate the runtime environment and check its regular installation:

```powershell
conda activate WQBRAIN
python -m pip show wqb-cli
python -I -m wqb_cli --help
```

If the package is missing, install a built wheel using its actual path:

```powershell
python -m pip install path/to/wqb_cli-version-py3-none-any.whl
```

Do not repair runtime imports by adding the development checkout to PYTHONPATH or installing editable mode in WQBRAIN. Source-based tests belong in a separate development environment.

### `WARNING: Ignoring invalid distribution ~qb-cli`

This is usually a stale pip uninstall/install artifact under `site-packages`. If the install succeeds, it does not block normal use. To clean it, inspect the active environment's `Lib/site-packages` directory and remove stale `~qb*` distribution folders.

### `wqb.exe is installed ... which is not on PATH`

Use the full Python module form or add the printed scripts directory to `PATH`:

```powershell
python -m wqb_cli --help
```

## Release

Package release:

[wqb-cli 0.4.0](https://github.com/untuitivist/wqb_cli/releases/tag/v0.4.0)

Release checklist:

1. Update `version` in `pyproject.toml`.
2. Run editable install.
3. Run tests.
4. Commit changes.
5. Tag the release, for example `v0.4.0`.
6. Push the branch and tag.
7. Publish a GitHub Release.

## Version History

The history below follows versions recorded by package metadata and GitHub releases. The old runtime-only `__version__ = "0.1.0"` value was stale and was never a published package version.

### 0.4.0 - 2026-08-18

- Added: command-plugin SDK; durable SQLite batch simulations with enqueue/resume/status/cancel/export; template-family manifest validation and terminal reports; two isolated A-M research workflows.
- Changed: global `204/401/429` session renewal, five additional batch-worker login attempts, server-driven `429 / Retry-After` backpressure, polling-first queue scheduling, and explicit simulate-versus-submit terminology.
- Preserved: ambiguous simulation POST outcomes, operational history, Alpha details, and PnL remain auditable instead of being blindly replayed or deleted.

### 0.3.2 - 2026-07-16

- Added: generic competition and consultant leaderboard scopes; competition Guidelines and FAQ helpers; complete SPC prompt-submission list/create/history/update commands; canonical endpoint inventory, examples, and tests.
- Changed: API inventory grew from 104 endpoints and 126 method cases to 109 endpoints and 134 method cases without dropping existing registrations; alpha requests can retry with Basic Auth after a cookie-session `401`; workflow constraints and README release documentation were expanded; runtime and package versions are now synchronized.
- Removed: obsolete analyst/PV vector sample JSON files and one redundant workflow document. No published CLI command or registered endpoint was removed.

### 0.3.1 - 2026-05-22

- Added: the agent-first `wqb` console command, package-local auth/config/community/scope/shortcut tools, bundled API inventory, generated command docs, alpha submit polling, smoke tests, bilingual README files, and project branding.
- Changed: package layout and metadata were rebuilt around `wqb_cli`; workflow and local-data documentation were expanded; licensing changed from MIT to GPL-3.0-only plus Commons Clause.
- Removed: the legacy `wqb_core` package-discovery/test layout and unused legacy resources.

### 0.2.5 - 2026-05-13

- Added: the initial packaged WorldQuant BRAIN API wrapper and agent-oriented workflow baseline with `requests`, `pandas`, and `msgpack` dependencies.
- Changed: none; this was the initial package-metadata baseline.
- Removed: none.

See [CHANGELOG.md](CHANGELOG.md) for the maintained release log.

## License

This project is licensed under GPL-3.0-only with the Commons Clause License Condition v1.0.

Required attribution:

```text
Original author: wiz
Original repository: https://github.com/untuitivist/wqb_cli
Author GitHub: https://github.com/untuitivist
```

The Commons Clause removes the right to sell the software as defined in [LICENSE](LICENSE). This means the source is available, but the project is not OSI open source.
