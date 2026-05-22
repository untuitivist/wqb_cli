# WQB Simulation CLI

`wqb sim` wraps simulation APIs.

Covered commands: `list`, `options`, `get`, `create`, `super-selection`.

Wait policy: `wqb sim create` creates the simulation and then waits for the final simulation result by default. For multi-simulation, child simulations are also waited and included under top-level `children`. `201 Created` is only the intermediate `201 Created, waiting for results...` state.

See `api_inventory/BUSINESS_CLI_COVERAGE.md` for the complete endpoint-to-command mapping.
