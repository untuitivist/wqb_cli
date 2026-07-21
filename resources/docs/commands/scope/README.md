# scope

Inspect local `data_all` scope data under `wqb_cli/local/data_all/`.

Data source boundary:

- This command does not call `api.worldquantbrain.com`.
- It reads local dataset-analysis files produced for the WebDataScope browser plugin.
- Source plugin: [leetesla/WebDataScope-WorldQuant](https://github.com/leetesla/WebDataScope-WorldQuant)
- The plugin repository does not currently publish a stable download location for its local data files.

The local files are:

- `info_data.bin`: compressed msgpack quick index for scope summaries and ranking.
- `all_data.pickle`: optional large pickle with per-scope alpha base/settings/IS/OS dataframes.
- `main.ipynb`: original loader notes.

Expected local layout:

```text
wqb_cli/local/data_all/
  info_data.bin
  all_data.pickle  # optional
  main.ipynb       # optional
```

Commands:

- `wqb scope files`: show local files and sizes.
- `wqb scope list`: list available `REGION_DELAY` scopes.
- `wqb scope show <scope>`: show one scope summary.
- `wqb scope top <scope>`: rank datafields, datasets, or categories.
- `wqb scope search <scope> <query>`: search local scope items.
- `wqb scope neutralization <scope>`: inspect neutralization performance.
- `wqb scope pickle-summary <scope>`: load `all_data.pickle` and show table-level schema/sample rows.
- `wqb scope alpha-rows <scope>`: load `all_data.pickle` and read paged alpha detail rows.

Default path:

```text
wqb_cli/local/data_all/info_data.bin
```

Use `--info <path>` to read another quick index.
Use `--pickle <path>` to read another full pickle.

Use `info_data.bin` first for fast ranking. Use `all_data.pickle` only after a scope/field/dataset is worth inspecting, because it is much larger and loads slower.
