# Argument Examples

List files:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe scope files
```

List scopes:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe scope list
```

Show a scope:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe scope show USA_1
```

Top datafields:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe scope top USA_1 --group datafield --metric sharpe_ratio --min-count 5 --limit 10
```

Search datafields:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe scope search USA_1 volume --group datafield --limit 10
```

Neutralization ranking:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe scope neutralization USA_1 --group mean --metric sharpe_ratio
```

Full pickle table summary:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe scope pickle-summary USA_1 --sample 1
```

Full pickle alpha detail rows filtered by datafield:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe scope alpha-rows USA_1 --table base --datafield volume --limit 3 --columns id,datafield,dataset,category
```
