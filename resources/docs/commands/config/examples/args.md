# Argument Examples

Initialize config:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe config init
```

Set defaults:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe config set defaults.region USA
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe config set defaults.delay 1
```

Set auth email:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe config set auth.email user@example.com
```

Store password in keyring:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe config set-secret auth.password "<password>"
```

Login using keyring/config/env fallback:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe auth login
```

