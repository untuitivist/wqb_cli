# Release Checks

Run from repository root:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m pip install -e .
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m unittest discover -s tests
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m build
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m pip install --force-reinstall dist\wqb_cli-*.whl
wqb --help
wqb api stats
wqb config list
```

Local runtime data under `wqb_cli/local/` must not be included in release artifacts.
