# shortcut Notes

Shortcut commands are not a scheduler.
They only reduce API composition burden for common agent operations.

Simulation concurrency remains a caller responsibility:

- REGULAR concurrent simulations: at most 8 when `region != GLB`, at most 4 when `region == GLB`.
- SUPER concurrent simulations: at most 3.
- FASTEXPR multi-simulation batch size: up to 10 expressions; recommended 10 when `region != GLB`, 5 when `region == GLB`.
- REGULAR_PYTHON cannot use multi-simulation.

