# Release Checks

Run from repository root:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m pip install -e .
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m unittest discover -s tests
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m build
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m zipfile -l dist\wqb_cli-0.4.0-py3-none-any.whl
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m pip install --force-reinstall dist\wqb_cli-0.4.0-py3-none-any.whl
wqb --help
wqb sqlitesimu --help
wqb api stats
wqb config list
```

Inspect both the wheel and source archive before publishing. `local/`, `research_runs/`, credentials, cookies, SQLite databases, logs, and existing `build/`, `dist/`, or `*.egg-info` contents must not be included in release artifacts.
